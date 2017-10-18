from awacs.aws import (
    Action,
    Allow,
    Policy,
    Principal,
    Statement,
)

from troposphere import (
    Join,
    Region,
    AccountId,
)

from awacs import sts, s3, logs, ec2


def make_simple_assume_statement(*principals):
    return Statement(
        Principal=Principal('Service', principals),
        Effect=Allow,
        Action=[sts.AssumeRole])


def make_simple_assume_policy(*principals):
    return Policy(
        Statement=[
            make_simple_assume_statement(*principals)])


def s3_arn(bucket):
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
                s3.PutObjectAcl,
                s3.DeleteObject,
            ],
            Resource=object_buckets,
        ),
    ]


def read_write_s3_bucket_policy(buckets):
    return Policy(Statement=read_write_s3_bucket_policy_statements(buckets))


def log_stream_arn(log_group_name, log_stream_name):
    return Join(
        '',
        [
            "arn:aws:logs:", Region, ":", AccountId, ":log-group:",
            log_group_name, ":log-stream:", log_stream_name
        ]
    )


def write_to_cloudwatch_logs_stream_statements(log_group_name,
                                               log_stream_name):
    return [
        Statement(
            Effect=Allow,
            Action=[logs.PutLogEvents],
            Resource=[log_stream_arn(log_group_name, log_stream_name)]
        )
    ]


def write_to_cloudwatch_logs_stream_policy(log_group_name, log_stream_name):
    return Policy(
        Statement=write_to_cloudwatch_logs_stream_statements(log_group_name,
                                                             log_stream_name)
    )


def cloudwatch_logs_write_statements(log_group=None):
    resources = ["arn:aws:logs:*:*:*"]
    if log_group:
        log_group_parts = ["arn:aws:logs:", Region, ":", AccountId,
                           ":log-group:", log_group]
        log_group_arn = Join("", log_group_parts)
        log_stream_wild = Join("", log_group_parts + [":*"])
        resources = [log_group_arn, log_stream_wild]

    return [
        Statement(
            Effect=Allow,
            Resource=resources,
            Action=[
                logs.CreateLogGroup,
                logs.CreateLogStream,
                logs.PutLogEvents
            ]
        )
    ]


def lambda_basic_execution_statements(function_name):
    log_group = Join("/", ["/aws/lambda", function_name])
    return cloudwatch_logs_write_statements(log_group)


def lambda_basic_execution_policy(function_name):
    return Policy(Statement=lambda_basic_execution_statements(function_name))


def lambda_vpc_execution_statements():
    """Allow Lambda to manipuate EC2 ENIs for VPC support."""
    return [
        Statement(
            Effect=Allow,
            Resource=['*'],
            Action=[
                ec2.CreateNetworkInterface,
                ec2.DescribeNetworkInterfaces,
                ec2.DeleteNetworkInterface,
            ]
        )
    ]


def flowlogs_assumerole_policy():
    return make_simple_assume_policy("vpc-flow-logs.amazonaws.com")
