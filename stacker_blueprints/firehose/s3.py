from troposphere import firehose, Ref, GetAtt

from .base import Base


class S3Firehose(Base):

    def defined_variables(self):
        variables = super(S3Firehose, self).defined_variables()

        additional = {
            'StreamName': {
                'type': str,
                'description': 'The name of the firehose stream'
            }
        }

        variables.update(additional)
        return variables

    def create_delivery_stream(self):
        t = self.template
        variables = self.get_variables()
        prefix = self.context.get_fqn(self.name)

        stream_name = "%s_r101_etl_%s" % (
            prefix, variables['StreamName'])

        key_arn = self.get_kms_key_arn()
        bucket_arn = self.s3_arn(Ref('S3Bucket'))

        t.add_resource(firehose.DeliveryStream(
            'S3Firehose',
            DeliveryStreamName=stream_name,
            S3DestinationConfiguration=firehose.S3DestinationConfiguration(
                BucketARN=bucket_arn,
                RoleARN=GetAtt('IAMRole', 'Arn'),
                CompressionFormat='GZIP',
                BufferingHints=firehose.BufferingHints(
                    IntervalInSeconds=600,
                    SizeInMBs=50),
                Prefix='/',
                EncryptionConfiguration=firehose.EncryptionConfiguration(
                    KMSEncryptionConfig=firehose.KMSEncryptionConfig(
                        AWSKMSKeyARN=key_arn)),
                CloudWatchLoggingOptions=firehose.CloudWatchLoggingOptions(
                    Enabled=True,
                    LogGroupName='/aws/kinesisfirehose/%s' % (stream_name),
                    LogStreamName='S3Delivery'))))
