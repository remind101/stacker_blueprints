from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import TroposphereType

from troposphere import (
    iam,
    applicationautoscaling as aas,
    dynamodb,
    Ref,
    GetAtt,
    Output,
    Sub,
)

from .policies import (
    dynamodb_autoscaling_policy,
)


# TODO: Factor out the below two functions, once this PR is merged:
#  https://github.com/cloudtools/awacs/pull/93
# from awacs.helpers.trust import get_application_autoscaling_assumerole_policy
from awacs.helpers.trust import make_simple_assume_policy


def make_service_domain_name(service, region=''):
    """Helper function for creating proper service domain names."""
    tld = ".com.cn" if region == "cn-north-1" else ".com"
    return "{}.amazonaws{}".format(service, tld)


def get_application_autoscaling_assumerole_policy(region=''):
    """ Helper function for building the AWS Lambda AssumeRole Policy"""
    service = make_service_domain_name('application-autoscaling', region)
    return make_simple_assume_policy(service)

# end of TODO.


def snake_to_camel_case(name):
    """
    Accept a snake_case string and return a CamelCase string.
    For example::
      >>> snake_to_camel_case('cidr_block')
      'CidrBlock'
    """
    name = name.replace("-", "_")
    return "".join(word.capitalize() for word in name.split("_"))


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
    """Manages the AutoScaling of DynamoDB tables.

    Ref: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-dynamodb-table.html#cfn-dynamodb-table-examples-application-autoscaling # noqa

    Example::

      - name: dynamodb-autoscaling
        class_path: stacker_blueprints.dynamodb.AutoScaling
        variables:
          Tables:
            - test-user-table
            - test-group-table
          ReadCapacity: (5, 100)
          WriteCapacity: (5, 50)
    """
    VARIABLES = {
        "Tables": {
            "type": list,
            "description": "A list of DynamoDB tables to turn on autoscaling",
        },
        "ReadCapacity": {
            "type": list,
            "description": "Read (Min,Max) Capacity tuple.",
        },
        "WriteCapacity": {
            "type": list,
            "description": "Write (Min,Max) Capacity tuple.",
        },
        "ScaleInCooldown": {
            "type": int,
            "default": 60,
            "description": "Time in seconds to wait after scale in activity"
                           "completes before another scale in may start.",
        },
        "ScaleOutCooldown": {
            "type": int,
            "default": 60,
            "description": "Time in seconds to wait after scale out activity"
                           "completes before another scale out may start.",
        },
        "TargetValue": {
            "type": float,
            "default": 50.0,
            "description": "The target value for the metric.",
        },
    }

    def create_scaling_iam_role(self):
        assumerole_policy = get_application_autoscaling_assumerole_policy()
        return self.template.add_resource(
            iam.Role(
                "Role",
                Policies=[
                    iam.Policy(
                        PolicyName=Sub(
                            "${AWS::StackName}-dynamodb-autoscaling"
                        ),
                        PolicyDocument=dynamodb_autoscaling_policy(self.tables)
                    )
                ],
                AssumeRolePolicyDocument=assumerole_policy
            )
        )

    def create_scalable_target_and_policy(self, table, capacity_tuple, capacity_type): # noqa
        capacity_type = capacity_type.title()
        if capacity_type not in ("Write", "Read"):
            raise Exception("capacity_type must be either Write or Read.")
        dimension = "dynamodb:table:{}CapacityUnits".format(capacity_type)
        camel_table = snake_to_camel_case(table)
        scalable_target = self.template.add_resource(
           aas.ScalableTarget(
              "{}{}ScalableTarget".format(camel_table, capacity_type),
              MaxCapacity=capacity_tuple[0],
              MinCapacity=capacity_tuple[1],
              ResourceId=table,
              RoleARN=self.iam_role.ref(),
              ScalableDimension=dimension,
              ServiceNamespace="dynamodb"
           )
        )

        scaling_policy_name = "{}{}ScalablePolicy".format(
            camel_table,
            capacity_type
        )

        # https://docs.aws.amazon.com/autoscaling/application/APIReference/API_PredefinedMetricSpecification.html # noqa
        predefined_metric_spec = aas.PredefinedMetricSpecification( # noqa
            PredefinedMetricType="DynamoDB{}CapacityUtilization".format(capacity_type) # noqa
        )

        variables = self.get_variables()
        ttspc = aas.TargetTrackingScalingPolicyConfiguration(       # noqa
            TargetValue=variables["TargetValue"],
            ScaleInCooldown=variables["ScaleInCooldown"],
            ScaleOutCooldown=variables["ScaleOutCooldown"],
            PredefinedMetricSpecification=predefined_metric_spec,
        )

        # dynamodb only supports TargetTrackingScaling polcy type.
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-applicationautoscaling-scalingpolicy.html#cfn-applicationautoscaling-scalingpolicy-policytype # noqa
        self.template.add_resource(
            aas.ScalingPolicy(
                scaling_policy_name,
                PolicyName=scaling_policy_name,
                PolicyType="TargetTrackingScaling",
                ScalingTargetId=scalable_target.ref(),
                TargetTrackingScalingPolicyConfiguration=ttspc,
            )
        )

    def create_template(self):
        variables = self.get_variables()
        self.tables = variables["Tables"]
        self.iam_role = self.create_scaling_iam_role()
        for table in self.tables:
            self.create_scalable_target_and_policy(
                table, variables["ReadCapacity"], "read"
            )
            self.create_scalable_target_and_policy(
                table, variables["WriteCapacity"], "write"
            )
