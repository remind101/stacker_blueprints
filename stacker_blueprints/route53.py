from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import TroposphereType

from troposphere import route53


class DNSRecords(Blueprint):

    VARIABLES = {
        "RecordSets": {
            "type": TroposphereType(route53.RecordSetType, many=True),
            "description": "A dictionary of AWS::Route53::RecordSet types.""",
        },
        "DefaultHostedZoneId": {
            "type": str,
            "description": "If provided, this hosted zone id will be used for "
                           "any record that doesn't provide one. Note: "
                           "cannot be set if 'DefaultHostedZoneName' is set.",
            "default": "",
        },
        "DefaultHostedZoneName": {
            "type": str,
            "description": "If provided, this hosted zone id will be used for "
                           "any record that doesn't provide one. Note: "
                           "cannot be set if 'DefaultHostedZoneId' is set.",
            "default": "",
        },
    }

    def create_template(self):
        t = self.template
        variables = self.get_variables()
        default_zone_name = variables["DefaultHostedZoneName"]
        default_zone_id = variables["DefaultHostedZoneId"]

        if all([default_zone_name, default_zone_id]):
            raise ValueError("Cannot specify both 'DefaultHostedZoneName' and "
                             "'DefaultHostedZoneId' variables.")

        for record_set in variables["RecordSets"]:
            if default_zone_name and not getattr(record_set,
                                                 "HostedZoneName",
                                                 None):
                record_set.HostedZoneName = default_zone_name

            if default_zone_id and not getattr(record_set,
                                               "HostedZoneId",
                                               None):
                record_set.HostedZoneId = default_zone_id

            t.add_resource(record_set)
