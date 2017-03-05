from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import TroposphereType

from troposphere import (
    dynamodb,
    Ref,
    GetAtt,
    Output,
)


class DynamoDB(Blueprint):
    """Manages the creation of DynamoDB tables.

    Example::

      - name: users
        class_path: stacker_blueprints.dynamodb.DynamoDB
        variables:
          Tables:
            UserTable:
              TableName: prod-user-table
              KeySchema:
                - AttributeName: id
                  KeyType: HASH
                - AttributeName: name
                  KeyType: RANGE
              AttributeDefinitions:
                - AttributeName: id
                  AttributeType: S
                - AttributeName: name
                  AttributeType: S
              ProvisionedThroughput:
                ReadCapacityUnits: 5
                WriteCapacityUnits: 5
              StreamSpecification:
                StreamViewType: ALL

    """

    VARIABLES = {
        "Tables": {
            "type": TroposphereType(dynamodb.Table, many=True),
            "description": "DynamoDB tables to create.",
        }
    }

    def create_template(self):
        t = self.template
        variables = self.get_variables()
        for table in variables["Tables"]:
            t.add_resource(table)
            stream_enabled = table.properties.get("StreamSpecification")
            if stream_enabled:
                t.add_output(Output("{}StreamArn".format(table.title),
                                    Value=GetAtt(table, "StreamArn")))
            t.add_output(Output("{}Name".format(table.title),
                                Value=Ref(table)))
