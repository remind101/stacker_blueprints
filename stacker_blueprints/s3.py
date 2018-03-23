from stacker.blueprints.base import Blueprint
from troposphere import (
    FindInMap,
    GetAtt,
    Output,
    Sub,
    Ref,
    Region,
    s3,
    iam,
)

from .policies import (
    s3_arn,
    read_only_s3_bucket_policy,
    read_write_s3_bucket_policy,
    static_website_bucket_policy,
)

# reference:
#   https://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region
S3_WEBSITE_ENDPOINTS = {
    "us-east-2": {"endpoint": "s3-website.us-east-2.amazonaws.com"},
    "us-east-1": {"endpoint": "s3-website-us-east-1.amazonaws.com"},
    "us-west-1": {"endpoint": "s3-website-us-west-1.amazonaws.com"},
    "us-west-2": {"endpoint": "s3-website-us-west-2.amazonaws.com"},
    "ca-central-1": {"endpoint": "s3-website.ca-central-1.amazonaws.com"},
    "ap-south-1": {"endpoint": "s3-website.ap-south-1.amazonaws.com"},
    "ap-northeast-2": {"endpoint": "s3-website.ap-northeast-2.amazonaws.com"},
    "ap-southeast-1": {"endpoint": "s3-website-ap-southeast-1.amazonaws.com"},
    "ap-southeast-2": {"endpoint": "s3-website-ap-southeast-2.amazonaws.com"},
    "ap-northeast-1": {"endpoint": "s3-website-ap-northeast-1.amazonaws.com"},
    "eu-central-1": {"endpoint": "s3-website.eu-central-1.amazonaws.com"},
    "eu-west-1": {"endpoint": "s3-website-eu-west-1.amazonaws.com"},
    "eu-west-2": {"endpoint": "s3-website.eu-west-2.amazonaws.com"},
    "eu-west-3": {"endpoint": "s3-website.eu-west-3.amazonaws.com"},
    "sa-east-1": {"endpoint": "s3-website-sa-east-1.amazonaws.com"},
}


class Buckets(Blueprint):
    VARIABLES = {
        "Buckets": {
            "type": dict,
            "description": "A dictionary of buckets to create. The key "
                           "being the CFN logical resource name, the "
                           "value being a dictionary of attributes for "
                           "the troposphere s3.Bucket type.",
            "default": {}
        },
        "ReadWriteRoles": {
            "type": list,
            "description": "A list of roles that should have read/write "
                           "access to the buckets created.",
            "default": []
        },
        "ReadRoles": {
            "type": list,
            "description": "A list of roles that should have read-only "
                           "access to the buckets created.",
            "default": []
        },

    }

    def create_template(self):
        t = self.template
        variables = self.get_variables()

        bucket_ids = []

        for title, attrs in variables["Buckets"].items():
            bucket_id = Ref(title)
            t.add_resource(s3.Bucket.from_dict(title, attrs))
            t.add_output(Output(title + "BucketId", Value=bucket_id))
            t.add_output(Output(title + "BucketArn", Value=s3_arn(bucket_id)))
            t.add_output(
                Output(
                    title + "BucketDomainName",
                    Value=GetAtt(title, "DomainName")
                )
            )
            if "WebsiteConfiguration" in attrs:
                t.add_mapping("WebsiteEndpoints", S3_WEBSITE_ENDPOINTS)

                t.add_resource(
                    s3.BucketPolicy(
                        title + "BucketPolicy",
                        Bucket=bucket_id,
                        PolicyDocument=static_website_bucket_policy(bucket_id),
                    )
                )
                t.add_output(
                    Output(
                        title + "WebsiteUrl",
                        Value=GetAtt(title, "WebsiteURL")
                    )
                )
                t.add_output(
                    Output(
                        title + "WebsiteEndpoint",
                        Value=FindInMap(
                            "WebsiteEndpoints", Region, "endpoint"
                        )
                    )
                )

            bucket_ids.append(bucket_id)

        read_write_roles = variables["ReadWriteRoles"]
        if read_write_roles:
            t.add_resource(
                iam.PolicyType(
                    "ReadWritePolicy",
                    PolicyName=Sub("${AWS::StackName}ReadWritePolicy"),
                    PolicyDocument=read_write_s3_bucket_policy(
                        bucket_ids
                    ),
                    Roles=read_write_roles,
                )
            )

        read_only_roles = variables["ReadRoles"]
        if read_only_roles:
            t.add_resource(
                iam.PolicyType(
                    "ReadPolicy",
                    PolicyName=Sub("${AWS::StackName}ReadPolicy"),
                    PolicyDocument=read_only_s3_bucket_policy(
                        bucket_ids
                    ),
                    Roles=read_only_roles,
                )
            )
