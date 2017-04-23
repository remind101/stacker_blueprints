from troposphere import firehose

from .base import BaseDeliveryStream

DELIVERY_STREAM = "DeliveryStream"


class DeliveryStream(BaseDeliveryStream):
    def create_delivery_stream(self):
        t = self.template

        s3_dest_config = firehose.S3DestinationConfiguration(
            **self.s3_destination_config_dict()
        )

        self.delivery_stream = t.add_resource(
            firehose.DeliveryStream(
                DELIVERY_STREAM,
                S3DestinationConfiguration=s3_dest_config
            )
        )
