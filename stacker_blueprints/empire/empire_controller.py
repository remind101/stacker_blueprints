from troposphere import Ref, Output, GetAtt, FindInMap
from troposphere import ec2, autoscaling, ecs
from troposphere.autoscaling import Tag as ASTag
from troposphere.iam import InstanceProfile, Policy, Role

from awacs.helpers.trust import (
    get_default_assumerole_policy, get_ecs_assumerole_policy
)

from .empire_base import EmpireBase

from .policies import (
    service_role_policy,
    empire_policy,
    ecs_agent_policy,
)

CLUSTER_SG_NAME = "EmpireControllerSecurityGroup"


class EmpireController(EmpireBase):
    PARAMETERS = {
        "VpcId": {
            "type": "AWS::EC2::VPC::Id",
            "description": "Vpc Id"},
        "DefaultSG": {
            "type": "AWS::EC2::SecurityGroup::Id",
            "description": "Top level security group."},
        "PrivateSubnets": {
            "type": "List<AWS::EC2::Subnet::Id>",
            "description": "Subnets to deploy private instances in."},
        "AvailabilityZones": {
            "type": "CommaDelimitedList",
            "description": "Availability Zones to deploy instances in."},
        "InstanceType": {
            "type": "String",
            "description": "Empire AWS Instance Type",
            "default": "m3.medium"},
        "MinHosts": {
            "type": "Number",
            "description": "Minimum # of empire minion instances.",
            "default": "2"},
        "MaxHosts": {
            "type": "Number",
            "description": "Maximum # of empire minion instances.",
            "default": "3"},
        "SshKeyName": {
            "type": "AWS::EC2::KeyPair::KeyName"},
        "ImageName": {
            "type": "String",
            "description": "The image name to use from the AMIMap (usually "
                           "found in the config file.)",
            "default": "NAT"},
        "EmpireDBSecurityGroup": {
            "type": "AWS::EC2::SecurityGroup::Id",
            "description": "Security group of Empire database."},
    }

    def create_security_groups(self):
        t = self.template

        t.add_resource(
            ec2.SecurityGroup(
                CLUSTER_SG_NAME, GroupDescription=CLUSTER_SG_NAME,
                VpcId=Ref("VpcId")))
        t.add_output(
            Output('EmpireControllerSG', Value=Ref(CLUSTER_SG_NAME)))

        # Allow access to the DB
        t.add_resource(
            ec2.SecurityGroupIngress(
                "EmpireControllerDBAccess",
                IpProtocol='tcp', FromPort=5432, ToPort=5432,
                SourceSecurityGroupId=Ref(CLUSTER_SG_NAME),
                GroupId=Ref('EmpireDBSecurityGroup')))

    def create_ecs_cluster(self):
        t = self.template
        t.add_resource(ecs.Cluster("EmpireControllerCluster"))
        t.add_output(
            Output("ControllerECSCluster", Value=Ref("EmpireControllerCluster")))

    def build_block_device(self):
        volume = autoscaling.EBSBlockDevice(VolumeSize='50')
        return [autoscaling.BlockDeviceMapping(
            DeviceName='/dev/sdh', Ebs=volume)]

    def create_iam_profile(self):
        t = self.template
        ns = self.context.namespace
        # Create EC2 Container Service Role
        t.add_resource(
            Role(
                "ecsServiceRole",
                AssumeRolePolicyDocument=get_ecs_assumerole_policy(),
                Path="/",
                Policies=[
                    Policy(PolicyName="ecsServiceRolePolicy",
                           PolicyDocument=service_role_policy())
                ]))

        # Role for Empire Controllers
        t.add_resource(
            Role(
                "EmpireControllerRole",
                AssumeRolePolicyDocument=get_default_assumerole_policy(),
                Path="/",
                Policies=[
                    Policy(PolicyName="EmpireControllerPolicy",
                           PolicyDocument=empire_policy()),
                    Policy(PolicyName="%s-ecs-agent" % ns,
                           PolicyDocument=ecs_agent_policy()),
                ]))

        t.add_resource(
            InstanceProfile(
                "EmpireControllerProfile",
                Path="/",
                Roles=[Ref("EmpireControllerRole")]))
        t.add_output(
            Output("EmpireControllerRole",
                   Value=Ref("EmpireControllerRole")))

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
                'EmpireControllerLaunchConfig',
                IamInstanceProfile=GetAtt("EmpireControllerProfile",
                                          "Arn"),
                ImageId=FindInMap('AmiMap',
                                  Ref("AWS::Region"),
                                  Ref("ImageName")),
                BlockDeviceMappings=self.build_block_device(),
                InstanceType=Ref("InstanceType"),
                KeyName=Ref("SshKeyName"),
                UserData=self.generate_user_data(),
                SecurityGroups=[Ref("DefaultSG"), Ref(CLUSTER_SG_NAME)]))
        t.add_resource(
            autoscaling.AutoScalingGroup(
                'EmpireControllerAutoscalingGroup',
                AvailabilityZones=Ref("AvailabilityZones"),
                LaunchConfigurationName=Ref("EmpireControllerLaunchConfig"),
                MinSize=Ref("MinHosts"),
                MaxSize=Ref("MaxHosts"),
                VPCZoneIdentifier=Ref("PrivateSubnets"),
                LoadBalancerNames=[Ref("EmpireControllerLoadBalancer"), ],
                Tags=[ASTag('Name', 'empire_controller', True)]))

    def create_template(self):
        super(EmpireController, self).create_template()
