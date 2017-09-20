import unittest

from stacker.blueprints.testutil import BlueprintTestCase
from stacker.context import Context
from stacker.variables import Variable

from stacker_blueprints.aws_lambda import (
  Function,
  FunctionScheduler,
  Alias,
)

from troposphere.awslambda import Code


class TestFunction(BlueprintTestCase):
    def setUp(self):
        self.ctx = Context({'namespace': 'test'})

    def test_create_template(self):
        blueprint = Function('test_aws_lambda_Function', self.ctx)
        blueprint.resolve_variables(
            [
                Variable(
                    "Code",
                    Code(S3Bucket="test_bucket", S3Key="code_key")
                ),
                Variable("Description", "Test function."),
                Variable("Environment", {"TEST_NAME": "test_value"}),
                Variable("Runtime", "python2.7"),
            ]
        )
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_create_template_external_role(self):
        blueprint = Function('test_aws_lambda_Function_external_role',
                             self.ctx)
        blueprint.resolve_variables(
            [
                Variable(
                    "Code",
                    Code(S3Bucket="test_bucket", S3Key="code_key")
                ),
                Variable("Description", "Test function."),
                Variable("Environment", {"TEST_NAME": "test_value"}),
                Variable("Runtime", "python2.7"),
                Variable("Role", "my-fake-role"),
            ]
        )
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)


class TestFunctionScheduler(BlueprintTestCase):
    def setUp(self):
        self.ctx = Context({'namespace': 'test'})

    def test_create_template(self):
        blueprint = FunctionScheduler('test_aws_lambda_FunctionScheduler',
                                      self.ctx)
        blueprint.resolve_variables(
            [
                Variable(
                    "CloudwatchEventsRule",
                    {
                        "MyTestFuncSchedule": {
                            "Description": "The AWS Lambda schedule for "
                                           "my-powerful-test-function",
                            "ScheduleExpression": "rate(15 minutes)",
                            "State": "ENABLED",
                            "Targets": [
                                {
                                    "Id": "my-powerful-test-function",
                                    "Arn": "arn:aws:lambda:us-east-1:01234:"
                                           "function:my-Function-162L1234"
                                },
                            ],
                        }
                    }
                )
            ]
        )
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)


class TestAlias(BlueprintTestCase):
    def setUp(self):
        self.ctx = Context({'namespace': 'test'})

    def test_create_template(self):
        blueprint = Alias('test_aws_lambda_Alias', self.ctx)
        blueprint.resolve_variables(
            [
                Variable("Name", "prod"),
                Variable("FunctionName", "myFunction"),
                Variable("Version", "1"),
                Variable("Description", "The prod version of myFunction"),
            ]
        )
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)


if __name__ == '__main__':
    unittest.main()
