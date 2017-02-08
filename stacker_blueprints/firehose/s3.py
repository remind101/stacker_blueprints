from troposphere import firehose

from troposphere.logs import LogStream, LogGroup

from .base import Base

from ..policies import s3_arn

LOG_GROUP = 'LogGroup'
S3_LOG_STREAM = 'S3LogStream'


class S3Firehose(Base):

    def create_log_group(self, log_group_name):
        t = self.template
        prefix = self.context.get_fqn()
        log_stream_name = "%s-%s" % (prefix, S3_LOG_STREAM)

        t.add_resource(LogGroup(
            LOG_GROUP,
            LogGroupName=log_group_name
        ))

        t.add_resource(LogStream(
            'S3LogStream',
            LogGroupName=log_group_name,
            LogStreamName=log_stream_name,
            DependsOn=LOG_GROUP
        ))

    def create_delivery_stream(self):
        t = self.template
        variables = self.get_variables()
        prefix = self.context.get_fqn(self.name)

        stream_name = prefix

        log_group_name = '/aws/kinesisfirehose/%s' % (stream_name)

        self.create_log_group(log_group_name)

        key_arn = self.get_kms_key_arn()
        bucket_arn = s3_arn(self.get_firehose_bucket())
        role_arn = self.get_role_arn()
        s3_prefix = variables['S3Prefix'] or "/"

        t.add_resource(firehose.DeliveryStream(
            'S3Firehose',
            DeliveryStreamName=stream_name,
            S3DestinationConfiguration=firehose.S3DestinationConfiguration(
                BucketARN=bucket_arn,
                RoleARN=role_arn,
                CompressionFormat=variables['CompressionFormat'],
                BufferingHints=firehose.BufferingHints(
                    IntervalInSeconds=variables['IntervalInSeconds'],
                    SizeInMBs=variables['SizeInMBs']),
                Prefix=s3_prefix,
                EncryptionConfiguration=firehose.EncryptionConfiguration(
                    KMSEncryptionConfig=firehose.KMSEncryptionConfig(
                        AWSKMSKeyARN=key_arn)),
                CloudWatchLoggingOptions=firehose.CloudWatchLoggingOptions(
                    Enabled=True,
                    LogGroupName=log_group_name,
                    LogStreamName=S3_LOG_STREAM))))
