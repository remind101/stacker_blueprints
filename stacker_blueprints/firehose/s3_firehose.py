from troposphere import firehose

from stacker.blueprints.base import Blueprint


class S3Firehose(Blueprint):
    VARIABLES = {
        'StreamName': {
            'type': str,
            'description': 'The name of the firehose stream'
        },
        'KMSKey': {
            'type': str,
            'description': 'KMS key used for the firehose stream'},
        'Role': {
            'type': str,
            'description': 'IAM role for the firehose stream '
                           'stream to assume'},
        'Bucket': {
            'type': str,
            'description': 'The ARN of the bucket to '
                           'store events'}
    }

    def create_template(self):
        t = self.template
        variables = self.get_variables()
        prefix = self.context.get_fqn(self.name)

        stream_name = "%s_r101_etl_%s" % (
            prefix, variables['StreamName'])

        t.add_resource(firehose.DeliveryStream(
            'S3Firehose',
            DeliveryStreamName=stream_name,
            S3DestinationConfiguration=firehose.S3DestinationConfiguration(
                BucketARN="arn:aws:s3:::%s" % variables['Bucket'],
                RoleARN=variables['Role'],
                CompressionFormat='GZIP',
                BufferingHints=firehose.BufferingHints(
                    IntervalInSeconds=600,
                    SizeInMBs=50),
                Prefix='/',
                EncryptionConfiguration=firehose.EncryptionConfiguration(
                    KMSEncryptionConfig=firehose.KMSEncryptionConfig(
                        AWSKMSKeyARN=variables['KMSKey'])),
                CloudWatchLoggingOptions=firehose.CloudWatchLoggingOptions(
                    Enabled=True,
                    LogGroupName='/aws/kinesisfirehose/%s' % stream_name,
                    LogStreamName='S3Delivery'))))
