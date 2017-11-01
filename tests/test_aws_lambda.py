from types import MethodType

from stacker.context import Context
from stacker.config import Config
from stacker.variables import Variable
from stacker_blueprints.aws_lambda import Function, FunctionScheduler
from stacker.blueprints.testutil import BlueprintTestCase

from troposphere.awslambda import Code

from awacs.aws import Statement, Allow
import awacs.ec2


class TestBlueprint(BlueprintTestCase):
    def setUp(self):
        self.code = Code(S3Bucket="test_bucket", S3Key="code_key")
        self.common_variables = {
            "Code": self.code,
            "DeadLetterArn": "arn:aws:sqs:us-east-1:12345:dlq",
            "Description": "Test function.",
            "Environment": {"Env1": "Value1"},
            "Handler": "handler",
            "KmsKeyArn": "arn:aws:kms:us-east-1:12345:key",
            "MemorySize": 128,
            "Runtime": "python2.7",
            "Timeout": 3,
        }
        self.ctx = Context(config=Config({'namespace': 'test'}))

    def create_blueprint(self, name):
        return Function(name, self.ctx)

    def generate_variables(self):
        return [Variable(k, v) for k, v in self.common_variables.items()]

    def test_create_template_base(self):
        blueprint = self.create_blueprint('test_aws_lambda_Function')

        blueprint.resolve_variables(self.generate_variables())
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_create_template_with_external_role(self):
        blueprint = self.create_blueprint(
            'test_aws_lambda_Function_external_role'
        )
        self.common_variables["Role"] = "my-fake-role"

        blueprint.resolve_variables(self.generate_variables())
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_create_template_vpc_config(self):
        blueprint = self.create_blueprint(
            'test_aws_lambda_Function_with_vpc_config'
        )
        self.common_variables["VpcConfig"] = {
            "SecurityGroupIds": ["sg-1", "sg-2", "sg-3"],
            "SubnetIds": ["subnet-1", "subnet-2", "subnet-3"],
        }

        blueprint.resolve_variables(self.generate_variables())
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_create_template_with_alias_full_name_arn(self):
        blueprint = self.create_blueprint(
            'test_aws_lambda_Function_with_alias_full_name_arn'
        )
        self.common_variables["AliasName"] = ("arn:aws:lambda:aws-region:"
                                              "acct-id:function:helloworld:"
                                              "PROD")

        blueprint.resolve_variables(self.generate_variables())
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_create_template_with_alias_partial_name(self):
        blueprint = self.create_blueprint(
            'test_aws_lambda_Function_with_alias_partial_name'
        )
        self.common_variables["AliasName"] = "prod"

        blueprint.resolve_variables(self.generate_variables())
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_create_template_with_alias_provided_version(self):
        blueprint = self.create_blueprint(
            'test_aws_lambda_Function_with_alias_provided_version'
        )

        self.common_variables["AliasName"] = "prod"
        self.common_variables["AliasVersion"] = "1"

        blueprint.resolve_variables(self.generate_variables())
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_create_template_event_source_mapping(self):
        blueprint = self.create_blueprint(
            'test_aws_lambda_Function_event_source_mapping'
        )
        self.common_variables["EventSourceMapping"] = {
            "EventSourceArn": "arn:aws:dynamodb:us-east-1:12345:table/"
                              "FakeTable/stream/FakeStream",
            "StartingPosition": "0",
        }

        blueprint.resolve_variables(self.generate_variables())
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_create_template_extended_statements(self):
        blueprint = self.create_blueprint(
            'test_aws_lambda_Function_extended_statements'
        )

        def extended_statements(self):
            return [
                Statement(
                    Effect=Allow,
                    Resource=["*"],
                    Action=[awacs.ec2.DescribeInstances],
                )
            ]

        # Patch the extended_policy_statements method
        blueprint.extended_policy_statements = MethodType(
            extended_statements,
            blueprint
        )

        blueprint.resolve_variables(self.generate_variables())
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
