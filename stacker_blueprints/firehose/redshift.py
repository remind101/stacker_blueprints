from troposphere.firehose import (
    BufferingHints,
    CloudWatchLoggingOptions,
    CopyCommand,
    DeliveryStream,
    EncryptionConfiguration,
    KMSEncryptionConfig,
    RedshiftDestinationConfiguration,
    S3Configuration
)

from troposphere.logs import LogStream, LogGroup

from .base import Base

from stacker_blueprints.policies import (s3_arn)

S3_LOG_STREAM = 'S3Delivery'
REDSHIFT_LOG_STREAM = 'RedshiftDelivery'
LOG_GROUP = 'LogGroup'


class RedshiftFirehose(Base):

    def defined_variables(self):
        variables = super(RedshiftFirehose, self).defined_variables()

        additional = {
            'JDBCURL': {
                'type': str,
                'description': 'The URL used to connext to redshift'
            },
            'Username': {
                'type': str,
                'description': 'The user for the redshift table'
            },
            'Password': {
                'type': str,
                'description': 'The password for the redshift user'
            },
            'TableName': {
                'type': str,
                'description': 'The redshift table'
            }
        }

        variables.update(additional)

        return variables

    def create_log_group(self, log_group_name):
        t = self.template
        prefix = self.context.get_fqn()
        s3_stream_name = "%s-%s" % (prefix, S3_LOG_STREAM)
        redshift_stream_name = "%s-%s" % (prefix, REDSHIFT_LOG_STREAM)

        t.add_resource(LogGroup(
            LOG_GROUP,
            LogGroupName=log_group_name
        ))

        t.add_resource(LogStream(
            'S3LogStream',
            LogGroupName=log_group_name,
            LogStreamName=s3_stream_name,
            DependsOn=LOG_GROUP
        ))

        t.add_resource(LogStream(
            'RedshiftLogStream',
            LogGroupName=log_group_name,
            LogStreamName=redshift_stream_name,
            DependsOn=LOG_GROUP
        ))

    def create_redshift_firehose(self, stream_name, log_group_name):
        t = self.template
        variables = self.get_variables()

        copy_options = 'JSON \'auto\' ACCEPTINVCHARS BLANKSASNULL '
        copy_options += 'EMPTYASNULL GZIP STATUPDATE OFF COMPUPDATE OFF'

        default_s3_prefix = '%s/' % (variables['TableName'])

        s3_prefix = variables['S3Prefix'] or default_s3_prefix

        key_arn = self.get_kms_key_arn()
        bucket_arn = s3_arn(self.get_firehose_bucket())
        role_arn = self.get_role_arn()

        s3_logging_options = CloudWatchLoggingOptions(
            Enabled=True,
            LogGroupName=log_group_name,
            LogStreamName=S3_LOG_STREAM
        )

        redshift_logging_options = CloudWatchLoggingOptions(
            Enabled=True,
            LogGroupName=log_group_name,
            LogStreamName=REDSHIFT_LOG_STREAM
        )

        encryption_config = {}

        encryption_config = EncryptionConfiguration(
            KMSEncryptionConfig=KMSEncryptionConfig(
                AWSKMSKeyARN=key_arn
            )
        )

        redshift_config = RedshiftDestinationConfiguration(
            RoleARN=role_arn,
            ClusterJDBCURL=variables['JDBCURL'],
            CopyCommand=CopyCommand(
                CopyOptions=copy_options,
                DataTableName=variables['TableName']
            ),
            Username=variables['Username'],
            Password=variables['Password'],
            S3Configuration=S3Configuration(
                RoleARN=role_arn,
                BucketARN=bucket_arn,
                Prefix=s3_prefix,
                BufferingHints=BufferingHints(
                    SizeInMBs=variables['SizeInMBs'],
                    IntervalInSeconds=variables['IntervalInSeconds']
                ),
                CompressionFormat=variables['CompressionFormat'],
                CloudWatchLoggingOptions=s3_logging_options,
                EncryptionConfiguration=encryption_config
            ),
            CloudWatchLoggingOptions=redshift_logging_options
        )

        t.add_resource(
            DeliveryStream(
                'RedshiftFirehose',
                DeliveryStreamName=stream_name,
                RedshiftDestinationConfiguration=redshift_config
            )
        )

    def create_delivery_stream(self):
        prefix = self.context.get_fqn(self.name)

        stream_name = prefix

        log_group_name = '/aws/kinesisfirehose/%s' % (stream_name)

        self.create_log_group(log_group_name)
        self.create_redshift_firehose(stream_name, log_group_name)
