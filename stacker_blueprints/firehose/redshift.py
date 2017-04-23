from troposphere import firehose, logs, Output, Ref, GetAtt

from stacker.blueprints.variables.types import CFNString

from .base import BaseDeliveryStream

DELIVERY_STREAM = "DeliveryStream"
REDSHIFT_LOG_STREAM = "RedshiftLogStream"


class DeliveryStream(BaseDeliveryStream):
    def defined_variables(self):
        variables = super(DeliveryStream, self).defined_variables()

        additional = {
            "JDBCURL": {
                "type": str,
                "description": "The URL used to connect to redshift"
            },
            "Username": {
                "type": str,
                "description": "The user for the redshift table"
            },
            "Password": {
                "type": CFNString,
                "description": "The password for the redshift user",
                "no_echo": True,
            },
            "TableName": {
                "type": str,
                "description": "The redshift table"
            },
            "CopyOptions": {
                "type": str,
                "description": "Copy Options used by the redshift copy "
                               "command.",
                "default": "JSON 'auto' ACCEPTINVCHARS BLANKSASNULL "
                           "EMPTYASNULL GZIP STATUPDATE OFF COMPUPDATE OFF",
            },
        }

        variables.update(additional)
        return variables

    def create_log_stream(self):
        t = self.template
        super(DeliveryStream, self).create_log_stream()

        self.redshift_log_stream = t.add_resource(
            logs.LogStream(
                REDSHIFT_LOG_STREAM,
                LogGroupName=Ref(self.log_group),
                DependsOn=self.log_group.title
            )
        )

        t.add_output(
            Output(
                "RedshiftLogStreamName",
                Value=Ref(self.redshift_log_stream)
            )
        )

    def create_delivery_stream(self):
        t = self.template
        variables = self.get_variables()

        s3_dest_config = firehose.S3Configuration(
            **self.s3_destination_config_dict()
        )

        redshift_config = firehose.RedshiftDestinationConfiguration(
            RoleARN=GetAtt(self.role, "Arn"),
            ClusterJDBCURL=variables['JDBCURL'],
            CopyCommand=firehose.CopyCommand(
                CopyOptions=variables["CopyOptions"],
                DataTableName=variables['TableName']
            ),
            Username=variables['Username'],
            Password=variables['Password'].ref,
            S3Configuration=s3_dest_config,
            CloudWatchLoggingOptions=self.cloudwatch_logging_options(
                self.log_group,
                self.redshift_log_stream
            )
        )

        self.delivery_stream = t.add_resource(
            firehose.DeliveryStream(
                DELIVERY_STREAM,
                RedshiftDestinationConfiguration=redshift_config
            )
        )
