from awacs.aws import (
    Action,
    Allow,
    Bool,
    Condition,
    Policy,
    Principal,
    AWSPrincipal,
    Statement,
    StringEquals,
)
import awacs.logs
import awacs.s3
import awacs.kms
import awacs.firehose
from awacs import sts
from stacker.blueprints.base import Blueprint
from troposphere import (
    iam,
    kms,
    Join,
    GetAtt,
    Output,
    Ref
)

from stacker_blueprints.policies import (
    read_write_s3_bucket_policy_statements,
    s3_arn
)


BUCKET = 'S3Bucket'
IAM_ROLE = 'IAMRole'
ROLE_POLICY = 'RolePolicy'
FIREHOSE_WRITE_POLICY = 'FirehoseWriteAccess'
LOGS_POLICY = 'LogsPolicy'
S3_WRITE_POLICY = 'S3WriteAccess'
LOGS_WRITE_POLICY = 'LogsWriteAccess'
KMS_KEY = "EncryptionKey"
S3_CLIENT_POLICY = "S3ClientPolicy"


def logs_policy_statements():
    """Statements to allow profile to create and logs and 
    log streams 
    """
    return [
        Statement(
            Effect=Allow,
            Action=[
                awacs.logs.CreateLogStream,
                awacs.logs.CreateLogGroup,
            ],
            Resource=['*'],
        ),
    ]


def logs_policy():
    return Policy(Statement=logs_policy_statements())


def firehose_write_policy_statements():
    return [
        Statement(
            Effect=Allow,
            Action=[
                awacs.firehose.CreateDeliveryStream,
                awacs.firehose.DeleteDeliveryStream,
                awacs.firehose.DescribeDeliveryStream,
                awacs.firehose.PutRecord,
                awacs.firehose.PutRecordBatch
            ],
            Resource=['*'],
        ),
    ]


def firehose_write_policy():
    return Policy(Statement=firehose_write_policy_statements())


def logs_write_policy():
    statements = [
        Statement(
            Effect=Allow,
            Action=[
                awacs.logs.PutLogEvents,
            ],
            Resource=['*'],
        ),
    ]
    return Policy(Statement=statements)


def s3_write_policy(bucket):
    statements = [
        Statement(
            Effect=Allow,
            Action=[
                awacs.s3.AbortMultipartUpload,
                awacs.s3.GetBucketLocation,
                awacs.s3.GetObject,
                awacs.s3.ListBucket,
                awacs.s3.ListBucketMultipartUploads,
                awacs.s3.PutObject,
            ],
            Resource=[
                s3_arn(bucket),
                s3_arn(Join("/", [bucket, "*"]))
            ],
        ),
    ]
    return Policy(Statement=statements)


def kms_key_policy(key_use_arns, key_admin_arns):
    """ Creates a key policy for use of a KMS Key.

    key_use_arns is a list of arns that should have access to use the KMS
    key.
    """

    root_arn = Join(":", ["arn:aws:iam:", Ref("AWS::AccountId"), "root"])

    statements = []
    statements.append(
        Statement(
            Sid="Enable IAM User Permissions",
            Effect=Allow,
            Principal=AWSPrincipal(root_arn),
            Action=[
                Action("kms", "*"),
            ],
            Resource=["*"]
        )
    )

    if key_use_arns:
        statements.append(
            Statement(
                Sid="Allow use of the key",
                Effect=Allow,
                Principal=AWSPrincipal(key_use_arns),
                Action=[
                    awacs.kms.Encrypt,
                    awacs.kms.Decrypt,
                    awacs.kms.ReEncrypt,
                    awacs.kms.GenerateDataKey,
                    awacs.kms.GenerateDataKeyWithoutPlaintext,
                    awacs.kms.DescribeKey,
                ],
                Resource=["*"]
            )
        )

        statements.append(
            Statement(
                Sid="Allow attachment of persistent resources",
                Effect=Allow,
                Principal=AWSPrincipal(key_use_arns),
                Action=[
                    awacs.kms.CreateGrant,
                    awacs.kms.ListGrants,
                    awacs.kms.RevokeGrant,
                ],
                Resource=["*"],
                Condition=Condition(Bool("kms:GrantIsForAWSResource", True))
            )
        )

    if key_admin_arns:
        statements.append(
            Statement(
                Sid="Allow access for Key Administrators",
                Effect=Allow,
                Principal=AWSPrincipal(key_admin_arns),
                Action=[
                    Action("kms", "Create*"),
                    Action("kms", "Describe*"),
                    Action("kms", "Enable*"),
                    Action("kms", "List*"),
                    Action("kms", "Put*"),
                    Action("kms", "Update*"),
                    Action("kms", "Revoke*"),
                    Action("kms", "Disable*"),
                    Action("kms", "Get*"),
                    Action("kms", "Delete*"),
                    Action("kms", "ScheduleKeyDeletion"),
                    Action("kms", "CancelKeyDeletion"),
                ],
                Resource=["*"],
            )
        )

    return Policy(Version="2012-10-17", Id="key-default-1",
                  Statement=statements)


class Base(Blueprint):

    VARIABLES = {
        "RoleNames": {
            "type": list,
            "description": "A list of role names that should have access to "
                           "write to the firehose stream.",
            "default": [],
        },
        "GroupNames": {
            "type": list,
            "description": "A list of group names that should have access to "
                           "write to the firehose stream.",
            "default": [],
        },
        "UserNames": {
            "type": list,
            "description": "A list of user names that should have access to "
                           "write to the firehose stream.",
            "default": [],
        },
        "ExistingBucketName": {
            "type": str,
            "description": "Name of the existing bucket"
        },
        "EncryptBucketData": {
            "type": bool,
            "description": "If set to true, a KMS key will be created to use "
                           "for encrypting the S3 Bucket's contents. If set "
                           "to false, no encryption will occur. Default: true",
            "default": True,
        },
        "EnableKeyRotation": {
            "type": bool,
            "description": "Whether to enable key rotation on the KMS key "
                           "generated if EncryptBucketData is set to true. "
                           "Default: true",
            "default": True,
        },
        "KeyUseArns": {
            "type": list,
            "description": "A list profile ARNs allowed to use KMS Key"
            "default": []
        },
        "KeyAdminArns": {
            "type": list,
            "description": "A list of profile ARNs that are KMS Key superusers"
            "default": [],
        },
        "SizeInMBs": {
            "type": int,
            "description": "Size in MBs for buffering hints for the Firehose "
                           "Delivery Stream"
        },
        "IntervalInSeconds": {
            "type": int,
            "description": "Buffering interval in seconds hints for the "
                           "Firehose Delivery Stream"
        },
        "CompressionFormat": {
            "type": str,
            "description": "The compression format used by the Firehose "
                           "Delivery Stream when storing data in the S3 bucket"
        },
        "S3Prefix": {
            "type": str,
            "description": "The prefix for folder in the S3 bucket",
            "default": ""
        }
    }

    def defined_variables(self):
        variables = super(Base, self).defined_variables()
        return variables

    def create_delivery_stream(self):
        raise NotImplementedError("create_delivery_stream must be implemented "
                                  "by a subclass")

    def get_kms_key_arn(self):
        key_arn = Join(
            "",
            [
                "arn:aws:kms:",
                Ref("AWS::Region"),
                ":",
                Ref("AWS::AccountId"),
                ":key/",
                Ref(KMS_KEY)
            ]
        )

        return key_arn

    def create_kms_key(self):
        t = self.template
        variables = self.get_variables()

        key_description = Join(
            "",
            [
                "S3 Bucket kms encryption key for stack ",
                Ref("AWS::StackName")
            ]
        )

        key_use_arns = variables["KeyUseArns"]
        # auto add the created IAM Role
        key_use_arns.append(GetAtt(IAM_ROLE, "Arn"))

        key_admin_arns = variables["KeyAdminArns"]

        if variables['EncryptBucketData']:
            t.add_resource(
                kms.Key(
                    KMS_KEY,
                    Description=key_description,
                    Enabled=True,
                    EnableKeyRotation=variables["EnableKeyRotation"],
                    KeyPolicy=kms_key_policy(key_use_arns, key_admin_arns)
                )
            )

        t.add_output(Output("KmsKeyArn", Value=self.get_kms_key_arn()))

    def get_firehose_bucket(self):
        return self.get_variables()['ExistingBucketName']

    def generate_iam_policies(self):
        name_prefix = self.context.get_fqn(self.name)

        s3_policy = iam.Policy(
            S3_WRITE_POLICY,
            PolicyName='{}-s3-write'.format(name_prefix),
            PolicyDocument=s3_write_policy(self.get_firehose_bucket()),
        )

        logs_policy = iam.Policy(
            LOGS_WRITE_POLICY,
            PolicyName='{}-logs-write'.format(name_prefix),
            PolicyDocument=logs_write_policy(),
        )
        return [s3_policy, logs_policy]

    def get_role_arn(self):
        return GetAtt(IAM_ROLE, 'Arn')

    def create_role(self):
        t = self.template

        statements = [
            Statement(
                Principal=Principal('Service', ['firehose.amazonaws.com']),
                Effect=Allow,
                Action=[sts.AssumeRole],
                Condition=Condition(
                    StringEquals('sts:ExternalId', Ref('AWS::AccountId')),
                ),
            ),
        ]

        firehose_role_policy = Policy(Statement=statements)

        t.add_resource(
            iam.Role(
                IAM_ROLE,
                AssumeRolePolicyDocument=firehose_role_policy,
                Path='/',
                Policies=self.generate_iam_policies(),
            ),

        )

        t.add_output(Output('Role', Value=Ref(IAM_ROLE)))
        t.add_output(Output('RoleArn', Value=GetAtt(IAM_ROLE, 'Arn')))

    def create_policy(self):
        t = self.template
        variables = self.get_variables()

        statements = firehose_write_policy_statements() + \
            logs_policy_statements() + \
            read_write_s3_bucket_policy_statements(
                [self.get_firehose_bucket()])

        roles = variables['RoleNames'] or Ref("AWS::NoValue")

        groups = variables['GroupNames'] or Ref("AWS::NoValue")

        users = variables['UserNames'] or Ref("AWS::NoValue")

        createPolicy = variables['RoleNames'] or variables[
            'GroupNames'] or variables['UserNames']

        if createPolicy:
            t.add_resource(
                iam.ManagedPolicy(
                    'ClientPolicy',
                    PolicyDocument=Policy(
                        Version='2012-10-17',
                        Statement=statements),
                    Roles=roles,
                    Groups=groups,
                    Users=users)
            )

    def create_template(self):
        self.create_kms_key()
        self.create_policy()
        self.create_role()
        self.create_delivery_stream()
