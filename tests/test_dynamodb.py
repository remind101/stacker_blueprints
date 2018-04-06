import unittest
from stacker.context import Context
from stacker.variables import Variable
from stacker.blueprints.testutil import BlueprintTestCase

import stacker_blueprints.dynamodb

class TestDynamoDB(BlueprintTestCase):
    def setUp(self):
        self.dynamodb_variables = [
            Variable(
              'Tables',
              {
                "UserTable": {
                  "TableName": "test-user-table",
                  "KeySchema": [
                    {
                      "AttributeName": "id",
                      "KeyType": "HASH",
                    },
                    {
                      "AttributeName": "name",
                      "KeyType": "RANGE",
                    },
                  ],
                  "AttributeDefinitions": [
                    {
                      "AttributeName": "id",
                      "AttributeType": "S",
                    },
                    {
                      "AttributeName": "name",
                      "AttributeType": "S",
                    },
                  ],
                  "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5,
                  },
                  "StreamSpecification": {
                    "StreamViewType": "ALL",
                  }
                }
              }
            )
        ]
        self.dynamodb_autoscaling_variables = [
            Variable(
              'Tables',
              ['test-user-table', 'test-group-table'],
            ),
            Variable(
              'ReadCapacity', [5, 100]
            ),
            Variable(
              'WriteCapacity', [5, 50]
            ),
        ]

    def test_dynamodb_table(self):
        ctx = Context({'namespace': 'test', 'environment': 'test'})
        blueprint = stacker_blueprints.dynamodb.DynamoDB('dynamodb_table', ctx)
        blueprint.resolve_variables(self.dynamodb_variables)
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_dynamodb_autoscaling(self):
        ctx = Context({'namespace': 'test', 'environment': 'test'})
        blueprint = stacker_blueprints.dynamodb.AutoScaling('dynamodb_autoscaling', ctx)
        blueprint.resolve_variables(self.dynamodb_autoscaling_variables)
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)
