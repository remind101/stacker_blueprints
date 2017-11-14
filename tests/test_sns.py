import unittest
from stacker.context import Context
from stacker.variables import Variable
from stacker_blueprints.sns import Topics
from stacker.blueprints.testutil import BlueprintTestCase

class TestBlueprint(BlueprintTestCase):
    def setUp(self):
        self.variables = [
            Variable('Topics', {
                'WithoutSubscription': {
                    'DisplayName': 'SampleTopicWithoutSub',
                },
                'Example': {
                    'DisplayName': 'ExampleTopic',
                    'Subscription': [
                        {
                            'Endpoint': 'arn:aws:sqs:us-east-1:123456788901:example-queue',
                            'Protocol': 'sqs',
                        },
                        {
                            'Endpoint': 'postmaster@example.com',
                            'Protocol': 'email',
                        },
                    ]
                },
            }),
        ]

    def test_sns(self):
        ctx = Context({'namespace': 'test', 'environment': 'test'})
        blueprint = Topics('topics', ctx)
        blueprint.resolve_variables(self.variables)
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)
