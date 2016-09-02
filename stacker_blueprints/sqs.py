from stacker.blueprints.base import Blueprint

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

    for key in queue.keys():
        # Check to see if there are any keys not the properties list.
        # If that's the case, bail since that could cause unexpected
        # outcomes.
        if key not in sqs_queue_properties:
            raise ValueError(
                "%s is not a valid SQS queue property" % key
            )

        if key == "RedrivePolicy":
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

        for name, queue_config in variables["Queues"].items():
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
