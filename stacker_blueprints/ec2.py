from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import TroposphereType

from troposphere import (
    ec2,
    Output,
)


class Instances(Blueprint):
    """ Manages the creation of EC2 Instance resources. """

    VARIABLES = {
        "Instances": {
            "type": TroposphereType(ec2.Instance, many=True),
            "description": "Dictionary of EC2 Instance definitions.",
        },
    }

    def create_template(self):
        t = self.template
        variables = self.get_variables()

        for instance in variables["Instances"]:
            t.add_resource(instance)
            title = instance.title
            t.add_output(
                Output(title + "InstanceId", Value=instance.Ref())
            )
            t.add_output(
                Output(
                    title + "AZ", Value=instance.GetAtt("AvailabilityZone")
                )
            )

            t.add_output(
                Output(
                    title + "PrivateDnsName",
                    Value=instance.GetAtt("PrivateDnsName")
                )
            )

            t.add_output(
                Output(
                    title + "PublicDnsName",
                    Value=instance.GetAtt("PublicDnsName")
                )
            )

            t.add_output(
                Output(
                    title + "PrivateIp",
                    Value=instance.GetAtt("PrivateIp")
                )
            )

            t.add_output(
                Output(
                    title + "PublicIp",
                    Value=instance.GetAtt("PublicIp")
                )
            )
