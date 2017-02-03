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
from awacs import sts
from stacker.blueprints.base import Blueprint
from troposphere import (
    iam,
    kms,
    s3,
    Equals,
    Join,
    GetAtt,
    Output,
    Ref,
    Not
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


def read_write_s3_bucket_policy_statements(buckets):
    list_buckets = [s3_arn(b) for b in buckets]
    object_buckets = [s3_arn(Join("/", [b, "*"])) for b in buckets]
    return [
        Statement(
            Effect="Allow",
            Action=[
                awacs.s3.GetBucketLocation,
                awacs.s3.ListAllMyBuckets,
            ],
            Resource=["arn:aws:s3:::*"]
        ),
        Statement(
            Effect=Allow,
            Action=[
                awacs.s3.ListBucket,
            ],
            Resource=list_buckets,
        ),
        Statement(
            Effect=Allow,
            Action=[
                awacs.s3.GetObject,
                awacs.s3.PutObject,
                awacs.s3.DeleteObject,
            ],
            Resource=object_buckets,
        ),
    ]


def read_write_s3_bucket_policy(buckets):
    return Policy(Statement=read_write_s3_bucket_policy_statements(buckets))


class FirehoseAction(Action):

    def __init__(self, action=None):
        self.prefix = "firehose"
        self.action = action


def s3_arn(bucket):
    return Join('', ['arn:aws:s3:::', bucket])


def logs_policy_statements():
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
                FirehoseAction("CreateDeliveryStream"),
                FirehoseAction("DeleteDeliveryStream"),
                FirehoseAction("DescribeDeliveryStream"),
                FirehoseAction("PutRecord"),
                FirehoseAction("PutRecordBatch"),
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


class FirehosePolicies(Blueprint):

    VARIABLES = {
        "RoleNames": {
            "type": list,
            "description": "A list of role names that should have access to "
                           "write to the firehose stream.",
            "default": "",
        },
        "GroupNames": {
            "type": list,
            "description": "A list of group names that should have access to "
                           "write to the firehose stream.",
            "default": "",
        },
        "UserNames": {
            "type": list,
            "description": "A list of user names that should have access to "
                           "write to the firehose stream.",
            "default": "",
        },
        "BucketName": {
            "type": str,
            "description": "Name for the S3 Bucket",
        },
        "EncryptS3Bucket": {
            "type": bool,
            "description": "If set to true, a KMS key will be created to use "
                           "for encrypting the S3 Bucket's contents. If set "
                           "to false, no encryption will occur. Default: true",
            "default": True,
        },
        "EnableKeyRotation": {
            "type": bool,
            "description": "Whether to enable key rotation on the KMS key "
                           "generated if EncryptS3Bucket is set to true. "
                           "Default: true",
            "default": True,
        },
        "KeyUserArns": {
            "type": list,
            "default": []
        },
        "KeyAdminArns": {
            "type": list,
            "default": [],
        }
    }

    def create_kms_key(self):
        t = self.template
        variables = self.get_variables()

        t.add_condition(
            "EncryptS3Bucket",
            Not(Equals(variables["EncryptS3Bucket"], "false"))
        )

        key_description = Join(
            "",
            [
                "S3 Bucket kms encryption key for stack ",
                Ref("AWS::StackName")
            ]
        )

        key_use_arns = variables["KeyUserArns"]
        # auto add the created IAM Role
        key_use_arns.append(GetAtt(IAM_ROLE, "Arn"))

        key_admin_arns = variables["KeyAdminArns"]

        t.add_resource(
            kms.Key(
                KMS_KEY,
                Description=key_description,
                Enabled=True,
                EnableKeyRotation=variables["EnableKeyRotation"],
                KeyPolicy=kms_key_policy(key_use_arns, key_admin_arns),
                Condition="EncryptS3Bucket"
            )
        )
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

        t.add_output(Output("KmsKeyArn", Value=key_arn))

    def create_bucket(self):
        t = self.template
        variables = self.get_variables()

        t.add_resource(
            s3.Bucket(
                BUCKET,
                BucketName=variables['BucketName'],
            )
        )

        t.add_output(Output('Bucket', Value=Ref(BUCKET)))

    def generate_iam_policies(self):
        ns = self.context.namespace
        name_prefix = "%s-%s" % (ns, self.name)
        variables = self.get_variables()

        s3_policy = iam.Policy(
            S3_WRITE_POLICY,
            PolicyName='{}-s3-write'.format(name_prefix),
            PolicyDocument=s3_write_policy(variables['BucketName']),
        )

        logs_policy = iam.Policy(
            LOGS_WRITE_POLICY,
            PolicyName='{}-logs-write'.format(name_prefix),
            PolicyDocument=logs_write_policy(),
        )
        return [s3_policy, logs_policy]

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
            read_write_s3_bucket_policy_statements([variables['BucketName']])

        roles = variables['RoleNames'] if variables[
            'RoleNames'] else Ref("AWS::NoValue")

        groups = variables['GroupNames'] if variables[
            'GroupNames'] else Ref("AWS::NoValue")

        users = variables['UserNames'] if variables[
            'UserNames'] else Ref("AWS::NoValue")

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
        self.create_bucket()
        self.create_role()
