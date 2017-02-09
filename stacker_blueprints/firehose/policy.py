from stacker.blueprints.base import Blueprint

from awacs.aws import (
    Policy
)

from troposphere import (
    Ref, iam
)

from stacker_blueprints.policies import (
    logs_policy_statements,
    firehose_write_policy_statements,
    read_write_s3_bucket_policy_statements
)


class FirehosePolicy(Blueprint):

    VARIABLES = {
        "RoleNames": {
            "type": list,
            "description": "A list of role names that should have access to "
                           "write to the firehose stream.",
            "default": [],
        },
        "GroupNames": {
            "type": list,
            "description": "A list of group names that should have access to "
                           "write to the firehose stream.",
            "default": [],
        },
        "UserNames": {
            "type": list,
            "description": "A list of user names that should have access to "
                           "write to the firehose stream.",
            "default": [],
        },
        "BucketNames": {
            "type": list,
            "description": "List of buckets that will be readable and "
            "writable to by the given roles, groups, users and firehoses",
            "default": []
        }
    }

    def create_template(self):
        t = self.template
        variables = self.get_variables()

        statements = (firehose_write_policy_statements() +
                      logs_policy_statements() +
                      read_write_s3_bucket_policy_statements(
                      variables['BucketNames']))

        roles = variables['RoleNames'] or Ref("AWS::NoValue")

        groups = variables['GroupNames'] or Ref("AWS::NoValue")

        users = variables['UserNames'] or Ref("AWS::NoValue")

        createPolicy = (variables['RoleNames'] or variables[
            'GroupNames'] or variables['UserNames']
            or variables['BucketNames'])

        if createPolicy:
            t.add_resource(
                iam.ManagedPolicy(
                    'ClientPolicy',
                    PolicyDocument=Policy(
                        Version='2012-10-17',
                        Statement=statements),
                    Roles=roles,
                    Groups=groups,
                    Users=users)
            )
