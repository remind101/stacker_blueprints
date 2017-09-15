from hashlib import md5

from stacker.blueprints.base import Blueprint

from troposphere import (
    Ref,
    Output,
    GetAtt,
    Join,
    Region,
    route53,
)

import logging
logger = logging.getLogger(__name__)

# reference: http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-route53-aliastarget.html  # noqa
CLOUDFRONT_ZONE_ID = "Z2FDTNDATAQYW2"

# reference: http://docs.aws.amazon.com/general/latest/gr/rande.html
ELB_ZONE_IDS = {
    'us-east-2': 'Z3AADJGX6KTTL2',
    'us-east-1': 'Z35SXDOTRQ7X7K',
    'us-west-1': 'Z368ELLRRE2KJ0',
    'us-west-2': 'Z1H1FL5HABSF5',
    'ca-central-1': 'ZQSVJUPU6J1EY',
    'ap-south-1': 'ZP97RAFLXTNZK',
    'ap-northeast-2': 'ZWKZPGTI48KDX',
    'ap-southeast-1': 'Z1LMS91P8CMLE5',
    'ap-southeast-2': 'Z1GM3OXH4ZPM65',
    'ap-northeast-1': 'Z14GRHDCWA56QT',
    'eu-central-1': 'Z215JYRZR1TBD5',
    'eu-west-1': 'Z32O12XQLNTSW2',
    'eu-west-2': 'ZHURV8PSTC4K8',
    'sa-east-1': 'Z2P70J7HTTTPLU',
}

CF_DOMAIN = ".cloudfront.net."
ELB_DOMAIN = ".elb.amazonaws.com."


def get_record_set_md5(rs_name, rs_type):
    """Accept record_set Name and Type. Return MD5 sum of these values."""
    rs_name = rs_name.lower()
    rs_type = rs_type.upper()
    # Make A and CNAME records hash to same sum to support updates.
    rs_type = "ACNAME" if rs_type in ["A", "CNAME"] else rs_type
    return md5(rs_name + rs_type).hexdigest()


def add_hosted_zone_id_if_missing(record_set, hosted_zone_id):
    """Add HostedZoneId to Trophosphere record_set object if missing."""
    if not getattr(record_set, "HostedZoneId", None):
        record_set.HostedZoneId = hosted_zone_id
    return record_set


class DNSRecords(Blueprint):

    VARIABLES = {
        "VPC": {
            "type": str,
            "default": "",
            "description": "A VPC that you want to associate with "
                           "this hosted zone. When you specify this property, "
                           "AWS CloudFormation creates a private hosted zone.",
        },
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
        "Comment": {
            "type": str,
            "description": "The comment of a stacker managed HostedZone."
                           "Does nothing when HostedZoneId in variables.",
            "default": "",
        },
        "RecordSets": {
            "type": list,
            "description": "A list of dictionaries representing the attributes"
                           "of a troposphere.route53.RecordSetType object."
                           "Also accepts an optional 'Enabled' boolean.",
            "default": []
        },
    }

    def add_hosted_zone_id_for_alias_target_if_missing(self, rs):
        """Add proper hosted zone id to record set alias target if missing."""
        if getattr(rs, "AliasTarget", None):
            if not getattr(rs.AliasTarget, "HostedZoneId", None):
                if rs.AliasTarget.DNSName.endswith(CF_DOMAIN):
                    rs.AliasTarget.HostedZoneId = CLOUDFRONT_ZONE_ID
                elif rs.AliasTarget.DNSName.endswith(ELB_DOMAIN):
                    elb_region = rs.AliasTarget.DNSName.split('.')[-5]
                    rs.AliasTarget.HostedZoneId = ELB_ZONE_IDS[elb_region]
                else:
                    rs.AliasTarget.HostedZoneId = self.hosted_zone_id
        return rs

    def create_record_set(self, rs_dict):
        """Accept a record_set dict. Return a Troposphere record_set object."""
        record_set_md5 = get_record_set_md5(rs_dict["Name"], rs_dict["Type"])
        rs = route53.RecordSetType.from_dict(record_set_md5, rs_dict)
        rs = add_hosted_zone_id_if_missing(rs, self.hosted_zone_id)
        rs = self.add_hosted_zone_id_for_alias_target_if_missing(rs)
        return self.template.add_resource(rs)

    def create_record_sets(self, record_set_dicts):
        """Accept list of record_set dicts.
        Return list of record_set objects."""
        record_set_objects = []
        for record_set_dict in record_set_dicts:
            # pop removes the 'Enabled' key and tests if True.
            if record_set_dict.pop('Enabled', True):
                record_set_objects.append(
                    self.create_record_set(record_set_dict)
                )
        return record_set_objects

    def create_template(self):
        variables = self.get_variables()
        hosted_zone_name = variables["HostedZoneName"]
        hosted_zone_id = variables["HostedZoneId"]
        hosted_zone_comment = variables["Comment"]

        if all([hosted_zone_comment, hosted_zone_id]):
            logger.warning(
                "The Comment variable works when HostedZoneName is passed."
                "When HostedZoneId in variables, Comment is ignored."
            )

        if all([hosted_zone_name, hosted_zone_id]):
            raise ValueError("Cannot specify both 'HostedZoneName' and "
                             "'HostedZoneId' variables.")

        if not any([hosted_zone_name, hosted_zone_id]):
            raise ValueError("Please specify either a 'HostedZoneName' or "
                             "'HostedZoneId' variable.")

        if hosted_zone_id:
            self.hosted_zone_id = hosted_zone_id

        else:
            hosted_zone_config = route53.HostedZoneConfiguration(
                "HostedZoneConfiguration",
                Comment=hosted_zone_comment
            )
            hosted_zone = route53.HostedZone(
                "HostedZone",
                Name=hosted_zone_name,
                HostedZoneConfig=hosted_zone_config
            )

            if variables["VPC"]:
                vpc = route53.HostedZoneVPCs(
                    VPCId=variables["VPC"],
                    VPCRegion=Region
                )
                hosted_zone.VPCs = [vpc]
            else:
                nameservers = Join(',', GetAtt(hosted_zone, "NameServers"))
                self.template.add_output(
                    Output("NameServers", Value=nameservers)
                )

            self.template.add_resource(hosted_zone)
            self.hosted_zone_id = Ref(hosted_zone)

        self.template.add_output(
            Output("HostedZoneId", Value=self.hosted_zone_id)
        )

        # return a list of troposphere record set objects.
        return self.create_record_sets(variables["RecordSets"])
