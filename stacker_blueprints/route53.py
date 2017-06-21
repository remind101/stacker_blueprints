from hashlib import md5

from stacker.blueprints.base import Blueprint

from troposphere import (
    Ref,
    Output,
    GetAtt,
    Join,
    route53,
)

CLOUDFRONT_HOSTED_ZONE_ID = "Z2FDTNDATAQYW2"


def get_record_set_md5(rs_name, rs_type):
    """Accept record_set Name and Type. Return MD5 sum of these values."""
    return md5(rs_name + rs_type).hexdigest()


def add_hosted_zone_id_if_missing(record_set, hosted_zone_id):
    """Add HostedZoneId to Trophosphere record_set object if missing."""
    if not getattr(record_set, "HostedZoneId", None):
        record_set.HostedZoneId = hosted_zone_id
    return record_set


def add_hosted_zone_id_for_cloudfront_alias_if_missing(record_set):
    """Accept a record_set Troposphere object. Returns record_set object."""
    # magic to automatically add the HostedZoneId for cloudfront.net aliases.
    # http://docs.aws.amazon.com/AWSCloudFormation/latest
    #       /UserGuide/aws-properties-route53-aliastarget.html
    if getattr(record_set, "AliasTarget", None):
        if not getattr(record_set.AliasTarget, "HostedZoneId", None):
            if ".cloudfront.net" in record_set.AliasTarget.DNSName:
                record_set.AliasTarget.HostedZoneId = CLOUDFRONT_HOSTED_ZONE_ID
    return record_set


class DNSRecords(Blueprint):

    VARIABLES = {
        "HostedZoneId": {
            "type": str,
            "description": "The id of an existing HostedZone.",
            "default": "",
        },
        "HostedZoneName": {
            "type": str,
            "description": "The name of a HostedZone to create and manage.",
            "default": "",
        },
        "RecordSets": {
            "type": list,
            "description": "A list of dictionaries representing the attributes"
                           "of a troposphere.route53.RecordSetType object.",
            "default": []
        },
    }

    def create_record_set(self, rs_dict):
        """Accept a record_set dict. Return a Troposphere record_set object."""
        record_set_md5 = get_record_set_md5(rs_dict["Name"], rs_dict["Type"])
        rs = route53.RecordSetType.from_dict(record_set_md5, rs_dict)
        rs = add_hosted_zone_id_if_missing(rs, self.hosted_zone_id)
        rs = add_hosted_zone_id_for_cloudfront_alias_if_missing(rs)
        return self.template.add_resource(rs)

    def create_record_sets(self, record_set_dicts):
        """Accept list of record_set dicts.
        Return list of record_set objects."""
        record_set_objects = []
        for record_set_dict in record_set_dicts:
            record_set_objects.append(self.create_record_set(record_set_dict))
        return record_set_objects

    def create_template(self):
        variables = self.get_variables()
        hosted_zone_name = variables["HostedZoneName"]
        hosted_zone_id = variables["HostedZoneId"]

        if all([hosted_zone_name, hosted_zone_id]):
            raise ValueError("Cannot specify both 'HostedZoneName' and "
                             "'HostedZoneId' variables.")

        if not any([hosted_zone_name, hosted_zone_id]):
            raise ValueError("Please specify either a 'HostedZoneName' or "
                             "'HostedZoneId' variable.")

        if hosted_zone_id:
            self.hosted_zone_id = hosted_zone_id

        else:
            self.template.add_resource(
                route53.HostedZone("HostedZone", Name=hosted_zone_name)
            )
            self.hosted_zone_id = Ref("HostedZone")
            self.nameservers = Join(',', GetAtt("HostedZone", "NameServers"))
            self.template.add_output(
                    Output("NameServers", Value=self.nameservers))

        self.template.add_output(
                Output("HostedZoneId", Value=self.hosted_zone_id))

        # return a list of troposphere record set objects.
        return self.create_record_sets(variables["RecordSets"])
