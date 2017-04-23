from stacker.blueprints.base import Blueprint
from troposphere import (
    Output,
    Ref,
    GetAtt,
    s3,
    iam,
)

from .policies import (
    read_only_s3_bucket_policy,
    read_write_s3_bucket_policy,
    s3_arn
)


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

        policy_prefix = self.context.get_fqn(self.name)

        bucket_ids = []

        for title, attrs in variables["Buckets"].items():
            t.add_resource(s3.Bucket.from_dict(title, attrs))
            t.add_output(Output(title + "BucketId", Value=Ref(title)))
            t.add_output(Output(title + "BucketArn", Value=s3_arn(Ref(title))))
            t.add_output(
                Output(
                    title + "BucketDomainName",
                    Value=GetAtt(title, "DomainName")
                )
            )
            if "WebsiteConfiguration" in attrs:
                t.add_output(
                    Output(
                        title + "WebsiteUrl",
                        Value=GetAtt(title, "WebsiteURL")
                    )
                )

            bucket_ids.append(Ref(title))

        read_write_roles = variables["ReadWriteRoles"]
        if read_write_roles:
            t.add_resource(
                iam.PolicyType(
                    "ReadWritePolicy",
                    PolicyName=policy_prefix + "ReadWritePolicy",
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
                    PolicyName=policy_prefix + "ReadPolicy",
                    PolicyDocument=read_only_s3_bucket_policy(
                        bucket_ids
                    ),
                    Roles=read_only_roles,
                )
            )
