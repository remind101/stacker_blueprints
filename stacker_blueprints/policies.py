from awacs.aws import Statement, Allow, Policy, Action

from troposphere import Join

from awacs import s3


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
                s3.DeleteObject,
            ],
            Resource=object_buckets,
        ),
    ]


def read_write_s3_bucket_policy(buckets):
    return Policy(Statement=read_write_s3_bucket_policy_statements(buckets))
