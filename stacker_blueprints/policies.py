from awacs.aws import (
    Statement, Allow, Policy, Action
)
from troposphere import Join

from awacs import (
    s3
)

import awacs


def s3_arn(bucket):
    """ Returns the arn for an s3 bucket. """
    return Join('', ['arn:aws:s3:::', bucket])


def read_only_s3_bucket_policy_statements(buckets):
    """ Read only policy an s3 bucket. """
    list_buckets = [s3_arn(b) for b in buckets]
    object_buckets = [s3_arn(Join("/", [b, "*"])) for b in buckets]

    bucket_resources = list_buckets + object_buckets

    return [
        Statement(
            Effect=Allow,
            Resource=[s3_arn("*")],
            Action=[s3.ListAllMyBuckets]
        ),
        Statement(
            Effect=Allow,
            Resource=bucket_resources,
            Action=[Action('s3', 'Get*'), Action('s3', 'List*')]
        )
    ]


def read_only_s3_bucket_policy(buckets):
    return Policy(Statement=read_only_s3_bucket_policy_statements(buckets))


def read_write_s3_bucket_policy_statements(buckets):
    list_buckets = [s3_arn(b) for b in buckets]
    object_buckets = [s3_arn(Join("/", [b, "*"])) for b in buckets]
    return [
        Statement(
            Effect="Allow",
            Action=[
                s3.GetBucketLocation,
                s3.ListAllMyBuckets,
            ],
            Resource=["arn:aws:s3:::*"]
        ),
        Statement(
            Effect=Allow,
            Action=[
                s3.ListBucket,
            ],
            Resource=list_buckets,
        ),
        Statement(
            Effect=Allow,
            Action=[
                s3.GetObject,
                s3.PutObject,
                s3.DeleteObject,
            ],
            Resource=object_buckets,
        ),
    ]


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


def read_write_s3_bucket_policy(buckets):
    return Policy(Statement=read_write_s3_bucket_policy_statements(buckets))
