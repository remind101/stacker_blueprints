from awacs.aws import (
    Action,
    Allow,
    Condition,
    Policy,
    Principal,
    Statement,
    StringEquals,
)
import awacs.logs
import awacs.s3
from awacs import sts
from stacker.blueprints.base import Blueprint
from troposphere import (
    iam,
    s3,
    Equals,
    GetAtt,
    If,
    Join,
    Not,
    Or,
    Output,
    Ref,
)

from troposphere import Condition as TropoCondition

BUCKET = 'S3Bucket'
IAM_ROLE = 'IAMRole'
ROLE_POLICY = 'RolePolicy'
FIREHOSE_WRITE_POLICY = 'FirehoseWriteAccess'
LOGS_POLICY = 'LogsPolicy'
S3_WRITE_POLICY = 'S3WriteAccess'
LOGS_WRITE_POLICY = 'LogsWriteAccess'


class FirehoseAction(Action):
    def __init__(self, action=None):
        self.prefix = "firehose"
        self.action = action


def logs_policy():
    statements = [
        Statement(
            Effect=Allow,
            Action=[
                awacs.logs.CreateLogStream,
                awacs.logs.CreateLogGroup,
            ],
            Resource=['*'],
        ),
    ]
    return Policy(Statement=statements)


def firehose_write_policy():
    statements = [
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
    return Policy(Statement=statements)


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

    def s3_arn(bucket):
        return Join('', ['arn:aws:s3:::', bucket])

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
                s3_arn(Join('/', [bucket, '*'])),
            ],
        ),
    ]
    return Policy(Statement=statements)


class Firehose(Blueprint):

    PARAMETERS = {
        "RoleNames": {
            "type": "CommaDelimitedList",
            "description": "A list of role names that should have access to "
                           "write to the firehose stream.",
            "default": "",
        },
        "GroupNames": {
            "type": "CommaDelimitedList",
            "description": "A list of group names that should have access to "
                           "write to the firehose stream.",
            "default": "",
        },
        "UserNames": {
            "type": "CommaDelimitedList",
            "description": "A list of user names that should have access to "
                           "write to the firehose stream.",
            "default": "",
        },
        "BucketName": {
            "type": "String",
            "description": "Name for the S3 Bucket",
        },
    }

    def create_bucket(self):
        t = self.template
        t.add_resource(
            s3.Bucket(
                BUCKET,
                BucketName=Ref('BucketName'),
            )
        )
        t.add_output(Output('Bucket', Value=Ref(BUCKET)))

    def generate_iam_policies(self):
        ns = self.context.namespace
        s3_policy = iam.Policy(
            S3_WRITE_POLICY,
            PolicyName='{}-s3-write'.format(ns),
            PolicyDocument=s3_write_policy(Ref('BucketName')),
        )
        logs_policy = iam.Policy(
            LOGS_WRITE_POLICY,
            PolicyName='{}-logs-write'.format(ns),
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
        ns = self.context.namespace
        t = self.template

        t.add_condition(
            'ExternalRoles',
            Not(Equals(Join(",", Ref('RoleNames')), '')),
        )
        t.add_condition(
            'ExternalGroups',
            Not(Equals(Join(",", Ref('GroupNames')), '')),
        )
        t.add_condition(
            'ExternalUsers',
            Not(Equals(Join(",", Ref('UserNames')), '')),
        )

        t.add_condition(
            'CreatePolicy',
            Or(
                TropoCondition("ExternalRoles"),
                TropoCondition("ExternalGroups"),
                TropoCondition("ExternalUsers"),
            )
        )

        t.add_resource(
            iam.PolicyType(
                FIREHOSE_WRITE_POLICY,
                PolicyName='{}-firehose'.format(ns),
                PolicyDocument=firehose_write_policy(),
                Roles=If("ExternalRoles",
                         Ref("RoleNames"),
                         Ref("AWS::NoValue")),
                Groups=If("ExternalGroups",
                          Ref("GroupNames"),
                          Ref("AWS::NoValue")),
                Users=If("ExternalUsers",
                         Ref("UserNames"),
                         Ref("AWS::NoValue")),
                Condition='CreatePolicy',
            ),
        )
        t.add_resource(
            iam.PolicyType(
                LOGS_POLICY,
                PolicyName='{}-logs'.format(ns),
                PolicyDocument=logs_policy(),
                Roles=If("ExternalRoles",
                         Ref("RoleNames"),
                         Ref("AWS::NoValue")),
                Groups=If("ExternalGroups",
                          Ref("GroupNames"),
                          Ref("AWS::NoValue")),
                Users=If("ExternalUsers",
                         Ref("UserNames"),
                         Ref("AWS::NoValue")),
                Condition='CreatePolicy',
            ),
        )

    def create_template(self):
        self.create_policy()
        self.create_bucket()
        self.create_role()
