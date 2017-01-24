from troposphere import Ref, ec2, FindInMap, Output, \
    GetAtt, Base64, Select
from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import (
    CFNString,
)


class Lamp(Blueprint):
    VARIABLES = {
        "SshKeyName": {
            "type": str
        },
        "InstanceType": {
            "type": str,
            "description": "EC2 Instance Type",
            "default": "m3.medium"
        },
        "ImageName": {
            "type": str,
            "description": "The image name to use from the AMIMap (usually "
                           "found in the config file.)",
            "default": "lamp"
        },
        "VpcId": {
            "type": str,
            "description": "Id of the VPC"
        },
        "Subnets": {
            "type": list,
            "description": "Subnets to deploy RDS instance in."
        },
        "UserData": {
            "type": Base64,
            "description": "The user - data file that will "
                           "be provided to the user"
        },
        "DBEndPoint": {
            "type": CFNString,
            "description": "The name of the database"
        },
        "MasterUser": {
            "type": CFNString,
            "description": "The name of the user"
        },
        "MasterUserPassword": {
            "type": CFNString,
            "description": "The password for the database"
        },
        "DatabaseName": {
            "type": CFNString,
            "description": "The name of the database"
        }
    }

    def create_security_group(self):
        t = self.template

        variables = self.get_variables()

        t.add_resource(ec2.SecurityGroup(
            'ServerSecurityGroup',
            GroupDescription='Server Security Group',
            VpcId=variables["VpcId"])
        )

    def create_ec2_instance(self):
        t = self.template

        variables = self.get_variables()

        t.add_resource(
            ec2.Instance(
                "LampInstance",
                ImageId=FindInMap(
                    'AmiMap', Ref("AWS::Region"), variables["ImageName"]),
                InstanceType=variables["InstanceType"],
                NetworkInterfaces=[
                    ec2.NetworkInterfaceProperty(
                        DeviceIndex=0,
                        AssociatePublicIpAddress=True,
                        GroupSet=[Ref('ServerSecurityGroup')],
                        SubnetId=Select(0, variables['Subnets']))],
                Tags=[ec2.Tag('Name', 'lamp-ec2-instance')],
                KeyName=variables['SshKeyName'],
                UserData=variables["UserData"],
            ),
        )

    def create_output(self):
        t = self.template

        t.add_output(
            Output('ServerSecurityGroup', Value=Ref('ServerSecurityGroup')))
        t.add_output(Output('LampInstance', Value=Ref('LampInstance')))
        t.add_output(
            Output('PublicDnsName',
                   Value=GetAtt('LampInstance', 'PublicDnsName')))

    def create_template(self):
        self.create_security_group()
        self.create_ec2_instance()
        self.create_output()
