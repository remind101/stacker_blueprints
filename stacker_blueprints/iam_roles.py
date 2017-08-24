from stacker.blueprints.base import Blueprint

from troposphere import (
    GetAtt,
    Output,
    Ref,
    iam,
)

from awacs.aws import Policy
from awacs.helpers.trust import (
    get_default_assumerole_policy,
    get_lambda_assumerole_policy
)


class Roles(Blueprint):
    VARIABLES = {
        "Ec2Roles": {
            "type": list,
            "description": "names of ec2 roles to create",
            "default": [],
        },
        "LambdaRoles": {
            "type": list,
            "description": "names of lambda roles to create",
            "default": [],
        },
    }

    def __init__(self, *args, **kwargs):
        super(Roles, self).__init__(*args, **kwargs)
        self.roles = []
        self.policies = []

    def create_role(self, name, assumerole_policy):
        t = self.template

        role = t.add_resource(
            iam.Role(
                name,
                AssumeRolePolicyDocument=assumerole_policy,
            )
        )

        t.add_output(
            Output(name + "RoleName", Value=Ref(role))
        )
        t.add_output(
            Output(name + "RoleArn", Value=GetAtt(role.title, "Arn"))
        )

        self.roles.append(role)
        return role

    def create_ec2_role(self, name):
        return self.create_role(name, get_default_assumerole_policy())

    def create_lambda_role(self, name):
        return self.create_role(name, get_lambda_assumerole_policy())

    def generate_policy_statements(self):
        """Should be overridden on a subclass to create policy statements.

        By subclassing this blueprint, and overriding this method to generate
        a list of :class:`awacs.aws.Statement` types, a
        :class:`troposphere.iam.PolicyType` will be created and attached to
        the roles specified here.

        If not specified, no Policy will be created.
        """

        return []

    def create_policy(self, name):
        statements = self.generate_policy_statements()
        if not statements:
            return

        t = self.template
        policy_prefix = self.context.get_fqn(self.name)

        policy = t.add_resource(
            iam.PolicyType(
                "{}Policy".format(name),
                PolicyName="{}-{}-policy".format(policy_prefix, name),
                PolicyDocument=Policy(
                    Statement=statements,
                ),
                Roles=[Ref(role) for role in self.roles],
            )
        )

        t.add_output(
            Output(name + "PolicyName", Value=Ref(policy))
        )
        self.policies.append(policy)

    def create_template(self):
        variables = self.get_variables()

        for role in variables['Ec2Roles']:
            self.create_ec2_role(role)

        for role in variables['LambdaRoles']:
            self.create_lambda_role(role)

        self.create_policy()
