import unittest

from stacker.blueprints.testutil import BlueprintTestCase
from stacker.context import Context
from stacker.config import Config
from stacker.variables import Variable

from stacker_blueprints.cloudwatch_logs import SubscriptionFilters

from troposphere import GetAtt, Ref


class TestSubscriptionFilters(BlueprintTestCase):
    def setUp(self):
        self.ctx = Context(config=Config({'namespace': 'test'}))

    def test_create_template(self):
        blueprint = SubscriptionFilters(
            'test_cloudwatch_logs_subscription_filters',
            self.ctx
        )

        blueprint.resolve_variables(
            [
                Variable(
                    "SubscriptionFilters",
                    {
                        "Filter1": {
                            "DestinationArn": GetAtt("KinesisStream1", "Arn"),
                            "FilterPattern": "{$.userIdentity.type = Root}",
                            "LogGroupName": Ref("LogGroup1"),
                        },
                        "Filter2": {
                            "DestinationArn": GetAtt("KinesisStream2", "Arn"),
                            "FilterPattern": "{$.userIdentity.type = Root}",
                            "LogGroupName": Ref("LogGroup2"),
                        },
                    }
                )
            ]
        )
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)


if __name__ == '__main__':
    unittest.main()
