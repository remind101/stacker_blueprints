import unittest

from stacker.blueprints.testutil import BlueprintTestCase
from stacker.context import Context
from stacker.variables import Variable

from stacker_blueprints.aws_lambda import Function

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


if __name__ == '__main__':
    unittest.main()
