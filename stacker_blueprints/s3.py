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
    s3_arn,
    s3_read_only_external_account_policy,
    s3_read_write_external_account_policy
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
        "ReadExternalArns": {
            "type": list,
            "description": "A list of external arns that have read-only "
                           "permissions for the created buckets",
            "default": []
        },
        "ReadWriteExternalArns": {
            "type": list,
            "description": "A list of external arns that have read-write "
                           "permissions for the created buckets",
            "default": []
        }

    }

    def additional_bucket_policies(self):
        # Overwrite this method in a subclass to add additional
        # policies to the s3 bucket.
        pass

    def add_bucket_policies(self, bucket_ids):
        policy_prefix = self.context.get_fqn(self.name)
        variables = self.get_variables()
        t = self.template

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

        read_external_arns = variables["ReadExternalArns"]
        if read_external_arns:
            for title, attrs in variables["Buckets"].items():

                bucket_name_without_dashes = title.replace('-', '')

                t.add_resource(
                    s3.BucketPolicy(
                        "ExternalPolicy%s" % bucket_name_without_dashes,
                        Bucket=Ref(title),
                        PolicyDocument=s3_read_only_external_account_policy(
                            read_external_arns, Ref(title)
                        )
                    )
                )

        write_external_arns = variables["ReadWriteExternalArns"]
        if write_external_arns:
            for title, attrs in variables["Buckets"].items():

                bucket_name_without_dashes = title.replace('-', '')

                t.add_resource(
                    s3.BucketPolicy(
                        "ExternalPolicy%s" % bucket_name_without_dashes,
                        Bucket=Ref(title),
                        PolicyDocument=s3_read_write_external_account_policy(
                            write_external_arns, Ref(title)
                        )
                    )
                )

    def create_buckets(self):
        t = self.template
        variables = self.get_variables()

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

            bucket_ids.append(Ref(title))

        return bucket_ids

    def create_template(self):

        # Create the buckets and return the ids
        bucket_ids = self.create_buckets()

        # Add common permissions to all the buckets
        self.add_bucket_policies(bucket_ids)

        # Allow subclasses to add custom permissions
        self.additional_bucket_policies()
