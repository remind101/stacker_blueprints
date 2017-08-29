import unittest
from stacker.context import Context
from stacker.variables import Variable
from stacker_blueprints.sqs import Queues
from stacker.blueprints.testutil import BlueprintTestCase

class TestBlueprint(BlueprintTestCase):
    def setUp(self):
        self.variables = [
            Variable('Queues', {
                'Simple': {
                    'DelaySeconds': 15,
                    'MaximumMessageSize': 4096,
                    'ReceiveMessageWaitTimeSeconds': 15,
                    'VisibilityTimeout': 600,
                },
                'Fifo': {
                    'FifoQueue': True,
                    'QueueName': 'Fifo.fifo',
                },
                'RedrivePolicy': {
                    'RedrivePolicy': {
                        'deadLetterTargetArn': 'arn:aws:sqs:us-east-1:123456789:dlq',
                        'maxReceiveCount': 3,
                    }
                }})
        ]

    def test_sqs(self):
        ctx = Context({'namespace': 'test', 'environment': 'test'})
        blueprint = Queues('queues', ctx)
        blueprint.resolve_variables(self.variables)
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)
