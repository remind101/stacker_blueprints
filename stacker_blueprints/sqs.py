from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import TroposphereType

from troposphere import (
    sqs,
    Ref,
    GetAtt,
    Output,
)


class Queues(Blueprint):
    """Manages the creation of SQS queues."""

    VARIABLES = {
        "Queues": {
            "type": TroposphereType(sqs.Queue, many=True),
            "description": "Dictionary of SQS queue definitions",
        },
    }

    def create_template(self):
        t = self.template
        variables = self.get_variables()

        for queue in variables["Queues"]:
            t.add_resource(queue)
            t.add_output(
                Output(queue.title + "Arn", Value=GetAtt(queue, "Arn"))
            )
            t.add_output(Output(queue.title + "Url", Value=Ref(queue)))
