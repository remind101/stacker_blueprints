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

    def test_dynamodb_table(self):
        ctx = Context({'namespace': 'test', 'environment': 'test'})
        blueprint = stacker_blueprints.dynamodb.DynamoDB('dynamodb_table', ctx)
        blueprint.resolve_variables(self.dynamodb_variables)
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)
