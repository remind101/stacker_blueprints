import copy

from troposphere import Ref, Output, GetAtt, FindInMap, If, Equals
from troposphere import ec2, autoscaling, ecs, logs
from troposphere.autoscaling import Tag as ASTag
from troposphere.iam import InstanceProfile, Policy, Role

from awacs.helpers.trust import (
    get_default_assumerole_policy,
)

from .empire_base import EmpireBase

from .policies import (
    ecs_agent_policy,
    runlogs_policy,
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
        "DisableRunLogs": {
            "type": "String",
            "description": (
                "Disables run logs if set to anything."
                " Note: Without this, Empire will log interactive runs to"
                " CloudWatch."
            ),
        },
    }

    def create_conditions(self):
        t = self.template
        t.add_condition(
            "EnableRunLogs",
            Equals(Ref("DisableRunLogs"), ""))

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

    def generate_iam_policies(self):
        base_policies = [
            Policy(
                PolicyName="ecs-agent",
                PolicyDocument=ecs_agent_policy(),
            ),
        ]
        with_logging = copy.deepcopy(base_policies)
        with_logging.append(
            Policy(
                PolicyName="runlogs",
                PolicyDocument=runlogs_policy(),
            ),
        )
        policies = If("EnableRunLogs", with_logging, base_policies)
        return policies

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

        def create_log_group(self):
            t = self.template
            t.add_resource(logs.LogGroup('RunLogs', Condition='EnableRunLogs'))
            t.add_output(Output('RunLogs', Value=Ref('RunLogs')))

        def create_template(self):
            super(EmpireController, self).create_template()
            self.create_log_group()
