from troposphere import (
    GetAtt,
    Join,
    Output,
    Ref,
    iam,
    logs,
    ec2,
)

from troposphere.iam import Policy as TropoPolicy

from stacker.blueprints.base import Blueprint

from awacs.aws import (
    Statement,
    Policy,
)

import awacs
import awacs.logs

from .policies import flowlogs_assumerole_policy
from .cloudwatch_logs import (
    LOG_RETENTION_STRINGS,
    validate_cloudwatch_log_retention
)

ALLOWED_TRAFFIC_TYPES = ["ACCEPT", "REJECT", "ALL"]
JOINED_TRAFFIC_TYPES = '/'.join(ALLOWED_TRAFFIC_TYPES)
LOG_RETENTION_DEFAULT = 0
CLOUDWATCH_ROLE_NAME = "Role"
FLOW_LOG_GROUP_NAME = "LogGroup"
FLOW_LOG_STREAM_NAME = "LogStream"


def vpc_flow_log_cloudwatch_policy(log_group_arn):
    return Policy(
        Statement=[
            Statement(
                Effect="Allow",
                Action=[
                    awacs.logs.DescribeLogGroups
                ],
                Resource=["*"],
            ),
            Statement(
                Effect="Allow",
                Action=[
                    awacs.logs.CreateLogStream,
                    awacs.logs.DescribeLogStreams,
                    awacs.logs.PutLogEvents,
                ],
                Resource=[
                    log_group_arn,
                    Join('', [log_group_arn, ":*"]),
                ],
            ),
        ]
    )


def validate_traffic_type(traffic_type):
    if traffic_type not in ALLOWED_TRAFFIC_TYPES:
        raise ValueError(
            "Traffic type must be one of the following: " +
            "%s" % JOINED_TRAFFIC_TYPES
        )

    return traffic_type


class FlowLogs(Blueprint):
    VARIABLES = {
        "Retention": {
            "type": int,
            "description": "Time in days to retain Cloudwatch Logs. Accepted "
                           "values: %s. Default 0 - retain forever." % (
                               ', '.join(LOG_RETENTION_STRINGS)),
            "default": LOG_RETENTION_DEFAULT,
            "validator": validate_cloudwatch_log_retention,

        },
        "VpcId": {
            "type": str,
            "description": "ID of the VPC that flow logs will be enabled "
                           "for.",
        },
        "TrafficType": {
            "type": str,
            "description": "Type of traffic to log. Must be one of the "
                           "following: %s" % JOINED_TRAFFIC_TYPES,
            "validator": validate_traffic_type,
            "default": "ALL",
        },
    }

    def create_template(self):
        t = self.template
        variables = self.get_variables()

        self.log_group = t.add_resource(
            logs.LogGroup(
                FLOW_LOG_GROUP_NAME,
                RetentionInDays=variables["Retention"],
            )
        )

        t.add_output(
            Output(
                "%sName" % FLOW_LOG_GROUP_NAME,
                Value=Ref(self.log_group)
            )
        )
        t.add_output(
            Output(
                "%sArn" % FLOW_LOG_GROUP_NAME,
                Value=GetAtt(self.log_group, "Arn")
            )
        )

        self.role = t.add_resource(
            iam.Role(
                CLOUDWATCH_ROLE_NAME,
                AssumeRolePolicyDocument=flowlogs_assumerole_policy(),
                Path="/",
                Policies=[
                    TropoPolicy(
                        PolicyName="vpc_cloudwatch_flowlog_policy",
                        PolicyDocument=vpc_flow_log_cloudwatch_policy(
                            GetAtt(self.log_group, "Arn")
                        ),
                    ),
                ]
            )
        )

        t.add_output(
            Output(
                "%sName" % CLOUDWATCH_ROLE_NAME,
                Value=Ref(self.role)
            )
        )
        role_arn = GetAtt(self.role, "Arn")
        t.add_output(
            Output(
                "%sArn" % CLOUDWATCH_ROLE_NAME,
                Value=role_arn
            )
        )

        self.log_stream = t.add_resource(
            ec2.FlowLog(
                FLOW_LOG_STREAM_NAME,
                DeliverLogsPermissionArn=role_arn,
                LogGroupName=Ref(FLOW_LOG_GROUP_NAME),
                ResourceId=variables["VpcId"],
                ResourceType="VPC",
                TrafficType=variables["TrafficType"],
            )
        )

        t.add_output(
            Output(
                "%sName" % FLOW_LOG_STREAM_NAME,
                Value=Ref(self.log_stream)
            )
        )
