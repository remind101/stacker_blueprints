import logging

from stacker.blueprints.base import Blueprint

from stacker.blueprints.variables.types import TroposphereType

from stacker.util import cf_safe_name

from troposphere import (
    NoValue,
    Output,
    Ref,
    Sub,
    iam,
)

from troposphere import awslambda

from troposphere import events

import awacs.logs
import awacs.kinesis
import awacs.dynamodb

from awacs.aws import Statement, Allow, Policy
from awacs.helpers.trust import get_lambda_assumerole_policy

from .policies import (
    lambda_basic_execution_statements,
    lambda_vpc_execution_statements,
)


logger = logging.getLogger(name=__name__)


def get_stream_action_type(stream_arn):
    """Returns the awacs Action for a stream type given an arn

    Args:
        stream_arn (str): The Arn of the stream.

    Returns:
        :class:`awacs.aws.Action`: The appropriate stream type awacs Action
            class

    Raises:
        ValueError: If the stream type doesn't match kinesis or dynamodb.
    """

    stream_type_map = {
        "kinesis": awacs.kinesis.Action,
        "dynamodb": awacs.dynamodb.Action,
    }

    stream_type = stream_arn.split(":")[2]
    try:
        return stream_type_map[stream_type]
    except KeyError:
        raise ValueError(
            "Invalid stream type '%s' in arn '%s'" % (stream_type, stream_arn)
        )


def stream_reader_statements(stream_arn):
    """Returns statements to allow Lambda to read from a stream.

    Handles both DynamoDB & Kinesis streams. Automatically figures out the
    type of stream, and provides the correct actions from the supplied Arn.

    Arg:
        stream_arn (str): A kinesis or dynamodb stream arn.

    Returns:
        list: A list of statements.
    """
    action_type = get_stream_action_type(stream_arn)
    arn_parts = stream_arn.split("/")
    # Cut off the last bit and replace it with a wildcard
    wildcard_arn_parts = arn_parts[:-1]
    wildcard_arn_parts.append("*")
    wildcard_arn = "/".join(wildcard_arn_parts)

    return [
        Statement(
            Effect=Allow,
            Resource=[stream_arn],
            Action=[
                action_type("DescribeStream"),
                action_type("GetRecords"),
                action_type("GetShardIterator"),
            ]
        ),
        Statement(
            Effect=Allow,
            Resource=[wildcard_arn],
            Action=[action_type("ListStreams")]
        )
    ]


class Function(Blueprint):
    VARIABLES = {
        "Code": {
            "type": awslambda.Code,
            "description": "The troposphere.awslambda.Code object "
                           "returned by the aws lambda hook.",
        },
        "DeadLetterArn": {
            "type": str,
            "description": "Dead Letter Queue (DLQ) Arn (SQS, SNS, etc) "
                           "that AWS Lambda (Lambda) sends events to when it "
                           "can't process them.",
            "default": "",
        },
        "Description": {
            "type": str,
            "description": "Description of the function.",
            "default": "",
        },
        "Environment": {
            "type": dict,
            "description": "Key-value pairs that Lambda caches and makes "
                           "available for your Lambda functions.",
            "default": {},
        },
        "Handler": {
            "type": str,
            "description": "The name of the function (within your source "
                           "code) that Lambda calls to start running your "
                           "code.",
            "default": "handler",
        },
        "KmsKeyArn": {
            "type": str,
            "description": "The Amazon Resource Name (ARN) of an AWS Key "
                           "Management Service (AWS KMS) key that Lambda "
                           "uses to encrypt and decrypt environment variable "
                           "values.",
            "default": "",
        },
        "MemorySize": {
            "type": int,
            "description": "The amount of memory, in MB, that is allocated "
                           "to your Lambda function. Default: 128",
            "default": 128,
        },
        "Runtime": {
            "type": str,
            "description": "The runtime environment for the Lambda function "
                           "that you are uploading.",
        },
        "Timeout": {
            "type": int,
            "description": "The function execution time (in seconds) after "
                           "which Lambda terminates the function. Default: 3",
            "default": 3,
        },
        "VpcConfig": {
            "type": dict,
            "description": "If the Lambda function requires access to "
                           "resources in a VPC, specify a VPC configuration "
                           "that Lambda uses to set up an elastic network "
                           "interface (ENI). Valid keys are: "
                           "SecurityGroupIds (a list of Ids), and SubnetIds "
                           "(a list of Ids). We automatically add an inline "
                           "policy to allow the lambda to create ENIs.",
            "default": {},
        },
        "Role": {
            "type": str,
            "description": "Arn of the Role to create the function as - if "
                           "not specified, a role will be created with the "
                           "basic permissions necessary for Lambda to run.",
            "default": "",
        },
        "AliasName": {
            "type": str,
            "description": "The name of an optional alias.",
            "default": "",
        },
        "AliasVersion": {
            "type": str,
            "description": "The version string for the alias without the "
                           "function Arn prepended.",
            "default": "$LATEST",
        },
        "EventSourceMapping": {
            "type": dict,
            "description": "An optional event source mapping config.",
            "default": {},
        },
    }

    def code(self):
        return self.get_variables()["Code"]

    def dead_letter_config(self):
        arn = self.get_variables()["DeadLetterArn"]
        dlc = NoValue
        if arn:
            dlc = awslambda.DeadLetterConfig(TargetArn=arn)
        return dlc

    def environment(self):
        environment = self.get_variables()["Environment"]
        env = NoValue
        if environment:
            env = awslambda.Environment(Variables=environment)
        return env

    def vpc_config(self):
        vpc_config = self.get_variables()["VpcConfig"]
        config = NoValue
        if vpc_config:
            if isinstance(vpc_config['SubnetIds'], str):
                vpc_config['SubnetIds'] = vpc_config['SubnetIds'].split(',')
            config = awslambda.VPCConfig(**vpc_config)
        return config

    def add_policy_statements(self, statements):
        """Adds statements to the policy.

        Args:
            statements (:class:`awacs.aws.Statement` or list): Either a single
                Statment, or a list of statements.
        """
        if isinstance(statements, Statement):
            statements = [statements]
        self._policy_statements.extend(statements)

    def extended_policy_statements(self):
        """Override this and add statements to add them to the lambda policy

        Returns:
            list: A list of :class:`awacs.aws.Statement` objects.
        """
        return []

    def generate_policy_statements(self):
        """Generates the policy statements for the role used by the function.

        To add additional statements you can either override the
        `extended_policy_statements` method to return a list of Statements
        to be added to the policy, or override this method itself if you
        need more control.

        Returns:
            list: A list of :class:`awacs.aws.Statement` objects.
        """
        statements = self._policy_statements
        statements.extend(
            lambda_basic_execution_statements(
                self.function.Ref()
            )
        )
        extended_statements = self.extended_policy_statements()
        if extended_statements:
            statements.extend(extended_statements)
        return statements

    def create_policy(self):
        t = self.template

        self.policy = t.add_resource(
            iam.PolicyType(
                "Policy",
                PolicyName=Sub("${AWS::StackName}-policy"),
                PolicyDocument=Policy(
                    Statement=self.generate_policy_statements()
                ),
                Roles=[self.role.Ref()],
            )
        )

        t.add_output(
            Output("PolicyName", Value=Ref(self.policy))
        )

    def create_role(self):
        t = self.template

        self.role = t.add_resource(
            iam.Role(
                "Role",
                AssumeRolePolicyDocument=get_lambda_assumerole_policy()
            )
        )

        if self.get_variables()["VpcConfig"]:
            # allow this Lambda to modify ENIs to allow it to run in our VPC.
            self.role.Policies = [
                iam.Policy(
                    PolicyName=Sub("${AWS::StackName}-vpc-policy"),
                    PolicyDocument=Policy(
                        Statement=lambda_vpc_execution_statements()
                    ),
                )
            ]

        t.add_output(
            Output("RoleName", Value=Ref(self.role))
        )

        role_arn = self.role.GetAtt("Arn")
        self.role_arn = role_arn

        t.add_output(
            Output("RoleArn", Value=role_arn)
        )

    def create_function(self):
        t = self.template
        variables = self.get_variables()

        self.function = t.add_resource(
            awslambda.Function(
                "Function",
                Code=self.code(),
                DeadLetterConfig=self.dead_letter_config(),
                Description=variables["Description"] or NoValue,
                Environment=self.environment(),
                Handler=variables["Handler"],
                KmsKeyArn=variables["KmsKeyArn"] or NoValue,
                MemorySize=variables["MemorySize"],
                Role=self.role_arn,
                Runtime=variables["Runtime"],
                Timeout=variables["Timeout"],
                VpcConfig=self.vpc_config(),
            )
        )

        t.add_output(
            Output("FunctionName", Value=self.function.Ref())
        )
        t.add_output(
            Output("FunctionArn", Value=self.function.GetAtt("Arn"))
        )

        self.function_version = t.add_resource(
            awslambda.Version(
                "LatestVersion",
                FunctionName=self.function.Ref()
            )
        )

        t.add_output(
            Output("LatestVersion",
                   Value=self.function_version.GetAtt("Version"))
        )
        t.add_output(
            Output("LatestVersionArn",
                   Value=self.function_version.Ref())
        )

        alias_name = variables["AliasName"]
        if alias_name:
            self.alias = t.add_resource(
                awslambda.Alias(
                    "Alias",
                    Name=alias_name,
                    FunctionName=self.function.Ref(),
                    FunctionVersion=variables["AliasVersion"] or "$LATEST",
                )
            )

            t.add_output(Output("AliasArn", Value=self.alias.Ref()))

    def create_event_source_mapping(self):
        t = self.template
        variables = self.get_variables()
        mapping = variables["EventSourceMapping"]
        if mapping:
            if "FunctionName" in mapping:
                logger.warn(
                    Sub("FunctionName defined in EventSourceMapping in "
                        "${AWS::StackName}. Overriding.")
                )
            mapping["FunctionName"] = self.function.GetAtt("Arn")
            resource = t.add_resource(
                awslambda.EventSourceMapping.from_dict(
                    "EventSourceMapping", mapping
                )
            )

            if not variables["Role"]:
                self.add_policy_statements(
                    stream_reader_statements(
                        mapping["EventSourceArn"]
                    )
                )

            t.add_output(
                Output("EventSourceMappingId", Value=resource.Ref())
            )

    def create_template(self):
        variables = self.get_variables()
        self._policy_statements = []
        role_arn = variables["Role"]
        # Set here - used in `create_role` to determine if an external role
        # was passed in. If an external role is passed in, no new role is
        # created, and no policies are generated/added to the external
        # role.
        self.role_arn = role_arn
        if not role_arn:
            self.create_role()
        self.create_function()
        self.create_event_source_mapping()
        # We don't use self.role_arn here because it is set internally if a
        # role is created
        if not role_arn:
            self.create_policy()


class FunctionScheduler(Blueprint):

    VARIABLES = {
        "CloudwatchEventsRule": {
            "type": TroposphereType(events.Rule),
            "description": "The troposphere.events.Rule object params.",
        },
    }

    def create_scheduler(self):
        variables = self.get_variables()
        troposphere_events_rule = variables["CloudwatchEventsRule"]
        aws_lambda_arns = {}

        # iterate over targets in the event Rule & gather aws_lambda_arns.
        for target in getattr(troposphere_events_rule, "Targets", []):
            if target.Arn.startswith("arn:aws:lambda:"):
                safe_id = cf_safe_name(target.Id)
                aws_lambda_arns[safe_id] = target.Arn

        # schedule a Cloudwatch event rule to invoke the Targets.
        rule = self.template.add_resource(troposphere_events_rule)

        # allow cloudwatch to invoke on any of the given lambda targets.
        for event_rule_target_id, aws_lambda_arn in aws_lambda_arns.items():
            self.template.add_resource(
                awslambda.Permission(
                    "PermToInvokeFunctionFor{}".format(event_rule_target_id),
                    Principal="events.amazonaws.com",
                    Action="lambda:InvokeFunction",
                    FunctionName=aws_lambda_arn,
                    SourceArn=rule.GetAtt("Arn")
                )
            )

    def create_template(self):
        self.create_scheduler()
