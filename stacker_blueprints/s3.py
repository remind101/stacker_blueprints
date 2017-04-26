from stacker.blueprints.base import Blueprint
from troposphere import (
    Output,
    Ref,
    GetAtt,
    s3,
    iam,
)

from awacs import Policy

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

    def __init__(self, *args, **kwargs):
        super(Buckets, self).__init__(*args, **kwargs)
        self._bucket_stmts = []
        self._bucket_ids = []

    def add_bucket_statements(self, stmts):
        self._bucket_statements.extend(stmts)

    @property
    def bucket_statements(self):
        stmts = self._bucket_statements
        stmts.extend(self.additional_bucket_statments())
        return stmts

    def bucket_policy_document(self):
        return Policy(
            Version='2012-10-17',
            Statement=self.bucket_statements)

    def create_bucket_policies(self):
        t = self.template
        variables = self.get_variables()
        stmts = self.bucket_statements

        if stmts:
            for title, attrs in variables["Buckets"].items():
                bucket_name_without_dashes = title.replace('-', '')
                t.add_resource(
                    s3.BucketPolicy(
                        "BucketPolicy-%s" % bucket_name_without_dashes,
                        Bucket=Ref(title),
                        PolicyDocument=self.bucket_policy_document()
                    )
                )

    def create_iam_policies(self):
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
                        self._bucket_ids
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
                        self._bucket_ids
                    ),
                    Roles=read_only_roles,
                )
            )

    def create_buckets(self):
        t = self.template
        variables = self.get_variables()

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

            self._bucket_ids.append(Ref(title))

    def create_template(self):

        # Create the buckets and return the ids
        self.create_buckets()

        # Add IAM policies
        self.create_iam_policies()

        # Add Bucket policies (some permissions cannot be express as IAM) 
        self.additional_bucket_policies()
