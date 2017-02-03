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

S3_LOG_STREAM = 'S3Delivery'
REDSHIFT_LOG_STREAM = 'RedshiftDelivery'


class RedshiftFirehose(Base):

    def defined_variables(self):
        variables = super(RedshiftFirehose, self).defined_variables()

        additional = {
            'StreamName': {
                'type': str,
                'description': 'The name of the firehose stream'
            },
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

    def create_log_group(self, stream_name, log_group_name):
        t = self.template

        t.add_resource(LogGroup(
            'LogGroup',
            LogGroupName=log_group_name
        ))

        t.add_resource(LogStream(
            'S3LogStream',
            LogGroupName=log_group_name,
            LogStreamName=S3_LOG_STREAM
        ))

        t.add_resource(LogStream(
            'RedshiftLogStream',
            LogGroupName=log_group_name,
            LogStreamName=REDSHIFT_LOG_STREAM
        ))

    def create_redshift_firehose(self, stream_name, log_group_name):
        t = self.template
        variables = self.get_variables()

        copy_options = 'JSON \'auto\' ACCEPTINVCHARS BLANKSASNULL '
        copy_options += 'EMPTYASNULL GZIP STATUPDATE OFF COMPUPDATE OFF'

        prefix = '{}/'.format(variables['TableName'])
        compression = 'GZIP'

        key_arn = self.get_kms_key_arn()
        bucket_arn = self.s3_arn(Ref('S3Bucket'))

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
                AWSKMSKeyARN=variables['KMSKey']
            )
        )

        redshift_config = RedshiftDestinationConfiguration(
            RoleARN=GetAtt('IAMRole', 'Arn'),
            ClusterJDBCURL=variables['JDBCURL'],
            CopyCommand=CopyCommand(
                CopyOptions=copy_options,
                DataTableName=variables['TableName']
            ),
            Username=variables['Username'],
            Password=variables['Password'],
            S3Configuration=S3Configuration(
                RoleARN=GetAtt('IAMRole', 'Arn'),
                BucketARN=bucket_arn,
                Prefix=prefix,
                BufferingHints=BufferingHints(
                    SizeInMBs=50,
                    IntervalInSeconds=600
                ),
                CompressionFormat=compression,
                CloudWatchLoggingOptions=s3_logging_options,
                EncryptionConfiguration=encryption_config
            ),
            CloudWatchLoggingOptions=redshift_logging_options
        )

        t.add_resource(
            DeliveryStream(
                'RedshiftFirhose',
                DeliveryStreamName=stream_name,
                RedshiftDestinationConfiguration=redshift_config
            )
        )

    def create_delivery_stream(self):
        variables = self.get_variables()
        prefix = self.context.get_fqn(self.name)

        stream_name = "%s_r101_etl_%s" % (
            prefix, variables['StreamName'])

        log_group_name = '/aws/kinesisfirehose/%s' % (stream_name)

        self.create_log_group(stream_name, log_group_name)
        self.create_redshift_firehose(stream_name, log_group_name)
