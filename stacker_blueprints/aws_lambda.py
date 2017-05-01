from stacker.blueprints.base import Blueprint

from troposphere import (
    GetAtt,
    Join,
    Output,
    Ref,
    iam,
)

from troposphere import awslambda

import awacs.logs
from awacs.aws import Statement, Allow, Policy
from awacs.helpers.trust import get_lambda_assumerole_policy

NoValue = Ref("AWS::NoValue")
Region = Ref("AWS::Region")
AccountId = Ref("AWS::AccountId")


def lambda_basic_execution_statements(log_group):
    """Basic policy statements for lambda functions.

    Gives Lambda permission to create the Cloudwatch Logs LogGroups and
    LogStreams it needs.
    """
    log_group_parts = ["arn:aws:logs:", Region, ":", AccountId,
                       ":log-group:", log_group]
    log_group_arn = Join("", log_group_parts)
    log_stream_wild = Join("", log_group_parts + [":*"])

    return [
        Statement(
            Effect=Allow,
            Resource=[
                log_group_arn,
                log_stream_wild,
            ],
            Action=[
                awacs.logs.CreateLogGroup,
                awacs.logs.CreateLogStream,
                awacs.logs.PutLogEvents
            ]
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
                           "(a list of Ids)",
            "default": {},
        }
    }

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
            config = awslambda.VPCConfig(**vpc_config)
        return config

    def generate_policy_statements(self):
        """Generates the policy statements for the role used by the function.

        You should override this, and extend the list that it returns with
        any additional iam policy statements you wish to give the role.

        Returns:
            list: A list of :class:`awacs.aws.Statement` objects.
        """
        log_group = Join("/", ["/aws/lambda", Ref(self.function)])
        return lambda_basic_execution_statements(log_group)

    def create_role(self):
        t = self.template

        self.role = t.add_resource(
            iam.Role(
                "Role",
                AssumeRolePolicyDocument=get_lambda_assumerole_policy(),
            )
        )

        t.add_output(
            Output("RoleName", Value=Ref(self.role))
        )
        t.add_output(
            Output("RoleArn", Value=GetAtt(self.role.title, "Arn"))
        )

    def create_function(self):
        t = self.template
        variables = self.get_variables()

        self.function = t.add_resource(
            awslambda.Function(
                "Function",
                Code=variables["Code"],
                DeadLetterConfig=self.dead_letter_config(),
                Description=variables["Description"] or NoValue,
                Environment=self.environment(),
                Handler=variables["Handler"],
                KmsKeyArn=variables["KmsKeyArn"] or NoValue,
                MemorySize=variables["MemorySize"],
                Role=GetAtt(self.role.title, "Arn"),
                Runtime=variables["Runtime"],
                Timeout=variables["Timeout"],
                VpcConfig=self.vpc_config(),
            )
        )

        t.add_output(
            Output("FunctionName", Value=Ref(self.function))
        )
        t.add_output(
            Output("FunctionArn", Value=GetAtt(self.function.title, "Arn"))
        )

    def create_policy(self):
        t = self.template
        policy_prefix = self.context.get_fqn(self.name)

        self.policy = t.add_resource(
            iam.PolicyType(
                "Policy",
                PolicyName="%s-policy" % policy_prefix,
                PolicyDocument=Policy(
                    Statement=self.generate_policy_statements()
                ),
                Roles=[Ref(self.role)],
            )
        )

        t.add_output(
            Output("PolicyName", Value=Ref(self.policy))
        )

    def create_template(self):
        self.create_role()
        self.create_function()
        self.create_policy()
