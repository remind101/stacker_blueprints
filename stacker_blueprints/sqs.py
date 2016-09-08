from stacker.blueprints.base import Blueprint
from . import util

from troposphere import (
    sqs,
    Ref,
    GetAtt,
    Output,
)


def check_queue(queue):
    sqs_queue_properties = [
        "DelaySeconds",
        "MaximumMessageSize",
        "MessageRetentionPeriod",
        "ReceiveMessageWaitTimeSeconds",
        "RedrivePolicy",
        "VisibilityTimeout",
    ]

    util.check_properties(queue, sqs_queue_properties, "SQS")

    if "RedrivePolicy" in queue:
        queue["RedrivePolicy"] = sqs.RedrivePolicy(**queue["RedrivePolicy"])

    return queue


class Queues(Blueprint):
    """Manages the creation of SQS queues."""

    VARIABLES = {
        "Queues": {
            "type": dict,
            "description": "Dictionary of SQS queue definitions",
        },
    }

    def create_template(self):
        variables = self.get_variables()

        for name, queue_config in variables["Queues"].iteritems():
            queue_config = check_queue(queue_config)
            self.create_queue(name, queue_config)

    def create_queue(self, queue_name, queue_config):
        t = self.template

        t.add_resource(
            sqs.Queue(
                queue_name, 
                **queue_config
            )
        )

        t.add_output(Output(queue_name + "Arn", Value=GetAtt(queue_name, "Arn")))
        t.add_output(Output(queue_name + "Url", Value=Ref(queue_name)))
