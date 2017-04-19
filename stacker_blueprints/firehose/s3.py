from troposphere import firehose

from .base import BaseDeliveryStream

DELIVERY_STREAM = "DeliveryStream"


class DeliveryStream(BaseDeliveryStream):
    def create_delivery_stream(self):
        t = self.template

        self.delivery_stream = t.add_resource(
            firehose.DeliveryStream(
                DELIVERY_STREAM,
                S3DestinationConfiguration=self.s3_destination_config()
            )
        )
