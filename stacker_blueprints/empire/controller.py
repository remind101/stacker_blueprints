from troposphere import (
    Ref,
    Output,
    GetAtt,
    FindInMap,
)
from troposphere import (
    ec2,
    autoscaling,
    ecs,
)
from troposphere.autoscaling import Tag as ASTag
from troposphere.iam import (
    InstanceProfile,
    Policy,
    Role,
)

from awacs.helpers.trust import (
    get_default_assumerole_policy,
)

from stacker.blueprints.variables.types import (
    CFNCommaDelimitedList,
    CFNNumber,
    CFNString,
    EC2KeyPairKeyName,
    EC2SecurityGroupId,
    EC2SubnetIdList,
    EC2VPCId,
)

from .base import EmpireBase

from .policies import ecs_agent_policy

CLUSTER_SG_NAME = "EmpireControllerSecurityGroup"


class EmpireController(EmpireBase):
    VARIABLES = {
        "VpcId": {
            "type": EC2VPCId,
            "description": "Vpc Id"},
        "DefaultSG": {
            "type": EC2SecurityGroupId,
            "description": "Top level security group."},
        "PrivateSubnets": {
            "type": EC2SubnetIdList,
            "description": "Subnets to deploy private instances in."},
        "AvailabilityZones": {
            "type": CFNCommaDelimitedList,
            "description": "Availability Zones to deploy instances in."},
        "InstanceType": {
            "type": CFNString,
            "description": "Empire AWS Instance Type",
            "default": "m3.medium"},
        "MinHosts": {
            "type": CFNNumber,
            "description": "Minimum # of empire minion instances.",
            "default": "2"},
        "MaxHosts": {
            "type": CFNNumber,
            "description": "Maximum # of empire minion instances.",
            "default": "3"},
        "SshKeyName": {
            "type": EC2KeyPairKeyName},
        "ImageName": {
            "type": CFNString,
            "description": (
                "The image name to use from the AMIMap (usually found in the "
                "config file.)"
            ),
            "default": "empire"},
        "DatabaseSecurityGroup": {
            "type": EC2SecurityGroupId,
            "description": "Security group of Empire database."},
        "DockerRegistry": {
            "type": CFNString,
            "description": (
                "Optional docker registry where private images are located."
            ),
            "default": "https://index.docker.io/v1/"},
        "DockerRegistryUser": {
            "type": CFNString,
            "description": "User for authentication with docker registry."},
        "DockerRegistryPassword": {
            "type": CFNString,
            "no_echo": True,
            "description": (
                "Password for authentication with docker registry."
            )},
        "DockerRegistryEmail": {
            "type": CFNString,
            "description": "Email for authentication with docker registry."},
    }

    def create_security_groups(self):
        t = self.template

        t.add_resource(
            ec2.SecurityGroup(
                CLUSTER_SG_NAME,
                GroupDescription=CLUSTER_SG_NAME,
                VpcId=Ref("VpcId")))

        t.add_output(
            Output("SecurityGroup", Value=Ref(CLUSTER_SG_NAME)))

        # Allow access to the DB
        t.add_resource(
            ec2.SecurityGroupIngress(
                "EmpireControllerDBAccess",
                IpProtocol="tcp", FromPort=5432, ToPort=5432,
                SourceSecurityGroupId=Ref(CLUSTER_SG_NAME),
                GroupId=Ref("DatabaseSecurityGroup")))

    def create_ecs_cluster(self):
        t = self.template
        t.add_resource(ecs.Cluster("EmpireControllerCluster"))
        t.add_output(
            Output("ECSCluster", Value=Ref("EmpireControllerCluster")))

    def build_block_device(self):
        volume = autoscaling.EBSBlockDevice(VolumeSize="50")
        return [autoscaling.BlockDeviceMapping(
            DeviceName="/dev/sdh", Ebs=volume)]

    def generate_iam_policies(self):
        return [
            Policy(
                PolicyName="ecs-agent",
                PolicyDocument=ecs_agent_policy(),
            )]

    def create_iam_profile(self):
        t = self.template
        # Role for Empire Controllers
        t.add_resource(
            Role(
                "EmpireControllerRole",
                AssumeRolePolicyDocument=get_default_assumerole_policy(),
                Path="/",
                Policies=self.generate_iam_policies()))

        t.add_resource(
            InstanceProfile(
                "EmpireControllerProfile",
                Path="/",
                Roles=[Ref("EmpireControllerRole")]))
        t.add_output(Output("IAMRole", Value=Ref("EmpireControllerRole")))

    def generate_seed_contents(self):
        seed = [
            "EMPIRE_HOSTGROUP=controller\n",
            "ECS_CLUSTER=", Ref("EmpireControllerCluster"), "\n",
            "DOCKER_REGISTRY=", Ref("DockerRegistry"), "\n",
            "DOCKER_USER=", Ref("DockerRegistryUser"), "\n",
            "DOCKER_PASS=", Ref("DockerRegistryPassword"), "\n",
            "DOCKER_EMAIL=", Ref("DockerRegistryEmail"), "\n",
        ]
        return seed

    def create_autoscaling_group(self):
        t = self.template
        t.add_resource(
            autoscaling.LaunchConfiguration(
                "EmpireControllerLaunchConfig",
                IamInstanceProfile=GetAtt("EmpireControllerProfile", "Arn"),
                ImageId=FindInMap(
                    "AmiMap",
                    Ref("AWS::Region"),
                    Ref("ImageName")),
                BlockDeviceMappings=self.build_block_device(),
                InstanceType=Ref("InstanceType"),
                KeyName=Ref("SshKeyName"),
                UserData=self.generate_user_data(),
                SecurityGroups=[Ref("DefaultSG"), Ref(CLUSTER_SG_NAME)]))
        t.add_resource(
            autoscaling.AutoScalingGroup(
                "EmpireControllerAutoscalingGroup",
                AvailabilityZones=Ref("AvailabilityZones"),
                LaunchConfigurationName=Ref("EmpireControllerLaunchConfig"),
                MinSize=Ref("MinHosts"),
                MaxSize=Ref("MaxHosts"),
                VPCZoneIdentifier=Ref("PrivateSubnets"),
                Tags=[ASTag("Name", "empire_controller", True)]))
