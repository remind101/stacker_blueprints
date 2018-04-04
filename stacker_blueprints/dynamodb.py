from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import TroposphereType

from troposphere import (
    applicationautoscaling,
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


class AutoScaling(Blueprint):
    VARIABLES = {
        "Tables": {
            "type": list,
            "description": "A list of DynamoDB tables to turn on autoscaling",
        },
        "ReadCapacity": {
            "type": tuple,
            "description": "Read (Min,Max) Capacity tuple.",
        },
        "WriteCapacity": {
            "type": tuple,
            "description": "Write (Min,Max) Capacity tuple.",
        },
    }

    def create_scaling_iam_role(self):
        pass

    def create_scalable_target(self, table, capacity_tuple, capacity_type):
        dimension = "dynamodb:table:{}CapacityUnits".format(
            capacity_type.title()
        )
        self.template.add_resource(
            applicationautoscaling.ScalableTarget(
               MaxCapacity=capacity_tuple[0],
               MinCapacity=capacity_tuple[1],
               ResourceId=table,
               RoleARN=self.iam_role.ref(),
               ScalableDimension=dimension,
               ServiceNamespace="dynamodb",
               # ScheduledActions,
            )
        )

    def create_template(self):
        variables = self.get_variables()
        self.iam_role = self.create_scaling_iam_role()
        for table in variables["Tables"]:
            self.create_create_scalable_target(
                table, variables["ReadCapacity"], "read"
            )
            self.create_create_scalable_target(
                table, variables["WriteCapacity"], "write"
            )
