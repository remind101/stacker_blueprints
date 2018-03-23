from awacs.aws import (
    Allow,
    Condition,
    Policy,
    Statement,
    StringEquals,
    StringLike,
)

import awacs.logs
import awacs.s3
import awacs.firehose
import awacs.kms
from awacs.helpers.trust import make_simple_assume_statement

from stacker.blueprints.base import Blueprint

from troposphere import (
    iam,
    logs,
    firehose,
    Join,
    GetAtt,
    Output,
    Ref,
    Sub,
)

from ..policies import (
    s3_arn,
    write_to_cloudwatch_logs_stream_statements,
)

from ..cloudwatch_logs import (
    LOG_RETENTION_STRINGS,
    validate_cloudwatch_log_retention,
)

LOG_GROUP = "LogGroup"
S3_LOG_STREAM = "S3LogStream"
ROLE = "Role"

REGION = Ref("AWS::Region")
NOVALUE = Ref("AWS::NoValue")


def make_simple_assume_policy(*principals):
    return Policy(
        Statement=[
            make_simple_assume_statement(*principals)
        ]
    )


def s3_write_statements(bucket_name):
    return [
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
                s3_arn(bucket_name),
                s3_arn(Join("/", [bucket_name, "*"]))
            ],
        ),
    ]


def kms_key_statements(key_arn, bucket_arn, bucket_prefix):
    s3_endpoint = Join(
        '',
        [
            "s3.", REGION, "amazonaws.com"
        ]
    )
    return [
        Statement(
            Effect=Allow,
            Action=[
                awacs.kms.Decrypt,
                awacs.kms.GenerateDataKey,
            ],
            Resource=[key_arn],
            Condition=Condition(
                [
                    StringEquals(
                        "kms:ViaService", s3_endpoint
                    ),
                    StringLike(
                        "kms:EncryptionContext:aws:s3:arn",
                        Join('', [bucket_arn, bucket_prefix, "*"])
                    )
                ]
            )

        )
    ]


class BaseDeliveryStream(Blueprint):
    VARIABLES = {
        "BucketName": {
            "type": str,
            "description": "Name of existing bucket to stream firehose "
                           "data to."
        },
        "S3Prefix": {
            "type": str,
            "description": "The prefix used when writing objects in the s3 "
                           "bucket.",
            "default": "/",
        },
        "EncryptionKeyArn": {
            "type": str,
            "description": "ARN of the KMS key to use to encrypt objects in "
                           "the s3 bucket.",
            "default": "",
        },
        "BufferingHints": {
            "type": dict,
            "description": "A dictionary with buffering hints for writing "
                           "objects to the s3 bucket. Valid keys are: "
                           "IntervalInSeconds, SizeInMBs",
            "default": {"IntervalInSeconds": 300, "SizeInMBs": 5},
        },
        "CompressionFormat": {
            "type": str,
            "description": "The compression format used by the Firehose when "
                           "writing objects in the s3 bucket.",
            "default": "UNCOMPRESSED",
        },
        "LogRetentionDays": {
            "type": int,
            "description": "Time in days to retain Cloudwatch Logs. Accepted "
                           "values: %s. Default 0 - retain forever." % (
                               ', '.join(LOG_RETENTION_STRINGS)),
            "default": 0,
            "validator": validate_cloudwatch_log_retention,
        }
    }

    def buffering_hints(self):
        hints_config = self.get_variables()["BufferingHints"]
        return firehose.BufferingHints(**hints_config)

    def encryption_config(self):
        key_arn = self.get_variables()["EncryptionKeyArn"]
        if key_arn:
            return firehose.EncryptionConfiguration(
                KMSEncryptionConfig=firehose.KMSEncryptionConfig(
                    AWSKMSKeyARN=key_arn
                )
            )
        else:
            return NOVALUE

    def s3_bucket_arn(self):
        bucket_name = self.get_variables()["BucketName"]
        return s3_arn(bucket_name)

    def cloudwatch_logging_options(self, log_group, log_stream):
        return firehose.CloudWatchLoggingOptions(
            Enabled=True,
            LogGroupName=Ref(log_group),
            LogStreamName=Ref(log_stream),
        )

    def s3_destination_config_dict(self):
        t = self.template
        variables = self.get_variables()

        t.add_output(Output("BucketName", Value=variables["BucketName"]))

        return {
            "BucketARN": self.s3_bucket_arn(),
            "RoleARN": GetAtt(self.role, "Arn"),
            "CompressionFormat": variables['CompressionFormat'],
            "BufferingHints": self.buffering_hints(),
            "Prefix": variables["S3Prefix"],
            "EncryptionConfiguration": self.encryption_config(),
            "CloudWatchLoggingOptions": self.cloudwatch_logging_options(
                self.log_group,
                self.s3_log_stream
            )
        }

    def generate_iam_policy_statements(self):
        variables = self.get_variables()
        bucket_name = variables["BucketName"]
        bucket_arn = self.s3_bucket_arn()
        s3_prefix = variables["S3Prefix"]
        key_arn = variables["EncryptionKeyArn"]

        statements = []
        statements.extend(s3_write_statements(bucket_name))
        statements.extend(
            write_to_cloudwatch_logs_stream_statements(
                Ref(self.log_group), Ref(self.s3_log_stream)
            )
        )

        if key_arn:
            statements.extend(
                kms_key_statements(
                    key_arn, bucket_arn, s3_prefix
                )
            )

        return statements

    def generate_iam_policy(self):
        return iam.Policy(
            PolicyName=Sub("${AWS::StackName}-policy"),
            PolicyDocument=Policy(
                Statement=self.generate_iam_policy_statements()
            )
        )

    def create_role(self):
        t = self.template

        self.role = t.add_resource(
            iam.Role(
                ROLE,
                AssumeRolePolicyDocument=make_simple_assume_policy(
                    "firehose.amazonaws.com"
                ),
                Path="/",
                Policies=[self.generate_iam_policy()]
            )
        )

        t.add_output(Output("RoleName", Value=Ref(self.role)))
        t.add_output(Output("RoleArn", Value=GetAtt(self.role, "Arn")))

    def create_log_group(self):
        t = self.template
        variables = self.get_variables()
        log_retention = variables["LogRetentionDays"] or NOVALUE

        self.log_group = t.add_resource(
            logs.LogGroup(
                LOG_GROUP,
                RetentionInDays=log_retention,
            )
        )

        t.add_output(Output("LogGroupName", Value=Ref(self.log_group)))
        t.add_output(
            Output("LogGroupArn", Value=GetAtt(self.log_group, "Arn"))
        )

    def create_s3_log_stream(self):
        t = self.template

        self.s3_log_stream = t.add_resource(
            logs.LogStream(
                S3_LOG_STREAM,
                LogGroupName=Ref(self.log_group),
                DependsOn=self.log_group.title
            )
        )

        t.add_output(Output("S3LogStreamName", Value=Ref(self.s3_log_stream)))

    def create_log_stream(self):
        self.create_s3_log_stream()

    def create_delivery_stream(self):
        raise NotImplementedError("create_delivery_stream must be implemented "
                                  "by a subclass.")

    def create_delivery_stream_output(self):
        t = self.template
        t.add_output(
            Output("DeliveryStreamName", Value=Ref(self.delivery_stream))
        )

    def create_template(self):
        self.create_log_group()
        self.create_log_stream()
        self.create_role()
        self.create_delivery_stream()
        self.create_delivery_stream_output()
