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

# reference:
#   https://docs.aws.amazon.com/general/latest/gr/rande.html#elb_region
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
    'eu-west-3': 'Z3Q77PNBQS71R4',
    'sa-east-1': 'Z2P70J7HTTTPLU',
}

# reference:
#   https://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region
S3_WEBSITE_ZONE_IDS = {
    "s3-website.us-east-2.amazonaws.com": "Z2O1EMRO9K5GLX",
    "s3-website-us-east-1.amazonaws.com": "Z3AQBSTGFYJSTF",
    "s3-website-us-west-1.amazonaws.com": "Z2F56UZL2M1ACD",
    "s3-website-us-west-2.amazonaws.com": "Z3BJ6K6RIION7M",
    "s3-website.ca-central-1.amazonaws.com": "Z1QDHH18159H29",
    "s3-website.ap-south-1.amazonaws.com": "Z11RGJOFQNVJUP",
    "s3-website.ap-northeast-2.amazonaws.com": "Z3W03O7B5YMIYP",
    "s3-website-ap-southeast-1.amazonaws.com": "Z3O0J2DXBE1FTB",
    "s3-website-ap-southeast-2.amazonaws.com": "Z1WCIGYICN2BYD",
    "s3-website-ap-northeast-1.amazonaws.com": "Z2M4EHUR26P7ZW",
    "s3-website.eu-central-1.amazonaws.com": "Z21DNDUVLTQW6Q",
    "s3-website-eu-west-1.amazonaws.com": "Z1BKCTXD74EZPE",
    "s3-website.eu-west-2.amazonaws.com": "Z3GKZC51ZF0DB4",
    "s3-website.eu-west-3.amazonaws.com": "Z3R1K369G5AVDG",
    "s3-website-sa-east-1.amazonaws.com": "Z7KQH4QJS55SO",
}


CF_DOMAIN = ".cloudfront.net."
ELB_DOMAIN = ".elb.amazonaws.com."
S3_WEBSITE_PREFIX = "s3-website"


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
        "RecordSetGroups": {
            "type": dict,
            "description": "A list of dictionaries representing the attributes"
                           "of a troposphere.route53.RecordSetGroup object."
                           "Also accepts an optional 'Enabled' boolean.",
            "default": {}
        },
    }

    def add_hosted_zone_id_for_alias_target_if_missing(self, rs):
        """Add proper hosted zone id to record set alias target if missing."""
        alias_target = getattr(rs, "AliasTarget", None)
        if alias_target:
            hosted_zone_id = getattr(alias_target, "HostedZoneId", None)
            if not hosted_zone_id:
                dns_name = alias_target.DNSName
                if dns_name.endswith(CF_DOMAIN):
                    alias_target.HostedZoneId = CLOUDFRONT_ZONE_ID
                elif dns_name.endswith(ELB_DOMAIN):
                    region = dns_name.split('.')[-5]
                    alias_target.HostedZoneId = ELB_ZONE_IDS[region]
                elif dns_name in S3_WEBSITE_ZONE_IDS:
                    alias_target.HostedZoneId = S3_WEBSITE_ZONE_IDS[dns_name]
                else:
                    alias_target.HostedZoneId = self.hosted_zone_id
        return rs

    def create_record_set(self, rs_dict):
        """Accept a record_set dict. Return a Troposphere record_set object."""
        record_set_md5 = get_record_set_md5(rs_dict["Name"], rs_dict["Type"])
        rs = route53.RecordSetType.from_dict(record_set_md5, rs_dict)
        rs = add_hosted_zone_id_if_missing(rs, self.hosted_zone_id)
        rs = self.add_hosted_zone_id_for_alias_target_if_missing(rs)
        return self.template.add_resource(rs)

    def create_record_set_group(self, name, g_dict):
        """Accept a record_set dict. Return a Troposphere record_set object."""
        rs = route53.RecordSetGroup.from_dict(name, g_dict)
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

    def create_record_set_groups(self, record_set_group_dicts):
        """Accept list of record_set_group dicts.
        Return list of record_set_group objects."""
        record_set_groups = []
        for name, group in record_set_group_dicts.iteritems():
            # pop removes the 'Enabled' key and tests if True.
            if group.pop('Enabled', True):
                record_set_groups.append(
                    self.create_record_set_group(name, group)
                )
        return record_set_groups

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

        self.create_record_set_groups(variables["RecordSetGroups"])
        return self.create_record_sets(variables["RecordSets"])
