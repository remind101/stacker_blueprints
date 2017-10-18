import unittest

from stacker.blueprints.testutil import BlueprintTestCase
from stacker.context import Context
from stacker.variables import Variable

from stacker_blueprints.aws_lambda import (
  Function,
  FunctionScheduler,
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

    def test_create_template_with_vpc_config(self):
        blueprint = Function('test_aws_lambda_function_with_vpc_config', self.ctx)
        blueprint.resolve_variables(
            [
                Variable(
                    "Code",
                    Code(S3Bucket="test_bucket", S3Key="code_key")
                ),
                Variable("Description", "Test function."),
                Variable("Environment", {"TEST_NAME": "test_value"}),
                Variable("Runtime", "python2.7"),
                Variable(
                    "VpcConfig",
                    {
                        "SecurityGroupIds": ['sg-12345678'],
                        "SubnetIds": "subnet-1111,subnet-2222,subnet-3333,subnet-4444"
                    }
                ),
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

    def test_create_template_with_alias_full_name_arn(self):
        blueprint = Function(
            'test_aws_lambda_Function_with_alias_full_name_arn',
            self.ctx
        )
        blueprint.resolve_variables(
            [
                Variable(
                    "Code",
                    Code(S3Bucket="test_bucket", S3Key="code_key")
                ),
                Variable("Description", "Test function."),
                Variable("Environment", {"TEST_NAME": "test_value"}),
                Variable("Runtime", "python2.7"),
                Variable("AliasName", "arn:aws:lambda:aws-region:"
                                      "acct-id:function:helloworld:PROD"),
            ]
        )
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_create_template_with_alias_partial_name(self):
        blueprint = Function(
            'test_aws_lambda_Function_with_alias_partial_name',
            self.ctx
        )
        blueprint.resolve_variables(
            [
                Variable(
                    "Code",
                    Code(S3Bucket="test_bucket", S3Key="code_key")
                ),
                Variable("Description", "Test function."),
                Variable("Environment", {"TEST_NAME": "test_value"}),
                Variable("Runtime", "python2.7"),
                Variable("AliasName", "prod"),
            ]
        )
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_create_template_with_alias_provided_version(self):
        blueprint = Function(
            'test_aws_lambda_Function_with_alias_provided_version',
            self.ctx
        )
        blueprint.resolve_variables(
            [
                Variable(
                    "Code",
                    Code(S3Bucket="test_bucket", S3Key="code_key")
                ),
                Variable("Description", "Test function."),
                Variable("Environment", {"TEST_NAME": "test_value"}),
                Variable("Runtime", "python2.7"),
                Variable("AliasName", "prod"),
                Variable("AliasVersion", "1")
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


if __name__ == '__main__':
    unittest.main()
