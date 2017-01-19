# Lamp Stack
#
# This stack configures our lamp host(s).
# http://en.wikipedia.org/wiki/Lamp_host
#
# These hosts are the only SSH entrypoint into the VPC. To SSH to a host inside
# the VPC you must first SSH to a lamp host, and then SSH from that host to
# another inside the VPC.

from troposphere import Ref, ec2, autoscaling, FindInMap, Output, GetAtt, Base64, Join, Select
from troposphere.autoscaling import Tag as ASTag

from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import (
    CFNCommaDelimitedList,
    CFNNumber,
    CFNString,
    EC2KeyPairKeyName,
    EC2SecurityGroupId,
    EC2SubnetIdList,
    EC2VPCId,
)

class Lamp(Blueprint):
    VARIABLES = {
        "SshKeyName": { "type": EC2KeyPairKeyName },
        "InstanceType": { 
            "type": CFNString,
            "description": "EC2 Instance Type",
            "default": "m3.medium"
         },
         "ImageName": {
            "type": CFNString,
            "description": "The image name to use from the AMIMap (usually "
                            "found in the config file.)",
            "default": "lamp"
         },
         "OfficeNetwork": {
            "type": CFNString,
            "description": "CIDR block allowed to access the ec2 hosts"
         },
         "VpcId" : {
            "type" : CFNString,
            "description": "Id of the VPC"
         },
         "DefaultSG" : {
            "type" : EC2SecurityGroupId,
            "description": "Default Security Group"
         },
         "Subnets": {
            "type": EC2SubnetIdList,
            "description": "Subnets to deploy RDS instance in."
        },
    }

    def create_security_group(self):
        t = self.template

        t.add_resource(ec2.SecurityGroup(
            'ServerSecurityGroup',
            GroupDescription='Server Security Group',
            VpcId=Ref("VpcId"))
        )
    
    def create_ec2_instance(self):
        t = self.template

        t.add_resource(
            ec2.Instance(
                "LampEC2Instance",
                ImageId=FindInMap('AmiMap', Ref("AWS::Region"), Ref("ImageName")),
                InstanceType=Ref("InstanceType"),
                NetworkInterfaces=[
                    ec2.NetworkInterfaceProperty(
                        DeviceIndex=0,
                        AssociatePublicIpAddress=True,
                        GroupSet=[Ref('ServerSecurityGroup')],
                        SubnetId=Select(0, Ref('Subnets')))],
                Tags=[ec2.Tag('Name', 'lamp-ec2-instance')],
                KeyName=Ref('SshKeyName'),
                UserData=Base64(
                    Join('',[
                        'bash',
                        'sudo apt-get -y update',
                        'sudo apt-get install -y apache2 php5'
                        'sudo apt-get install -y libapache2-mod-php5 php5-mcrypt php5-mysql'
                    ])
                ))
        )

    def create_output(self):
        t = self.template

        t.add_output(Output('ServerSecurityGroup', Value=Ref('ServerSecurityGroup')))
        t.add_output(Output('LampEC2Instance', Value=Ref('LampEC2Instance')))
        t.add_output(Output('PublicDnsName', Value=GetAtt('LampEC2Instance', 'PublicDnsName')))


    def create_template(self):
        self.create_security_group()
        self.create_ec2_instance()
        self.create_output()
        
