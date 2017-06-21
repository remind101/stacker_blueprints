import logging

from awacs.aws import (
    Allow,
    AWSPrincipal,
    Policy,
    Statement,
)

import awacs.kms

from troposphere import (
    Join,
    Output,
    Ref,
    kms,
)

from stacker.blueprints.base import Blueprint

logger = logging.getLogger(__name__)


def kms_key_root_statements():
    root_arn = Join(":", ["arn:aws:iam:", Ref("AWS::AccountId"), "root"])

    return [
        Statement(
            Sid="Enable IAM User Permissions",
            Effect=Allow,
            Principal=AWSPrincipal(root_arn),
            Action=[
                awacs.kms.Action("*"),
            ],
            Resource=["*"]
        )
    ]


def kms_key_policy():
    """ Creates a key policy for use of a KMS Key.  """

    statements = []
    statements.extend(kms_key_root_statements())

    return Policy(
        Version="2012-10-17",
        Id="root-account-access",
        Statement=statements
    )


class Key(Blueprint):
    VARIABLES = {
        "KeyAlias": {
            "type": str,
            "description": "The alias to give the key.",
            "default": "",
        },
        "Properties": {
            "type": dict,
            "description": "A dictionary of KMS key attributes which should "
                           "match the attributes for AWS::KMS::Key "
                           "Cloudformation resource. Note: You should "
                           "not supply a `KeyPolicy` attribute.",
            "default": {},
        },
        "Attributes": {
            "type": dict,
            "description": "Deprecated. Use Properties instead.",
            "default": {},
        }
    }

    def generate_key_policy(self):
        return kms_key_policy()

    def create_template(self):
        t = self.template
        variables = self.get_variables()

        key_policy = self.generate_key_policy()
        props = variables["Properties"]

        if variables["Attributes"]:
            raise DeprecationWarning(
                    "Attributes was deprecated, use Properties instead.")

        if "KeyPolicy" in props:
            logger.warning("KeyPolicy provided, but not used. To write "
                           "your own policy you need to subclass this "
                           "blueprint and override `generate_key_policy`.")
        props["KeyPolicy"] = key_policy

        key = t.add_resource(
            kms.Key.from_dict("Key", props)
        )

        key_arn = Join(
            "",
            [
                "arn:aws:kms:",
                Ref("AWS::Region"),
                ":",
                Ref("AWS::AccountId"),
                ":key/",
                Ref(key)
            ]
        )

        t.add_output(Output("KeyArn", Value=key_arn))
        t.add_output(Output("KeyId", Value=Ref(key)))

        key_alias = variables["KeyAlias"]
        if key_alias:
            if not key_alias.startswith("alias/"):
                key_alias = "alias/%s" % key_alias
            alias = t.add_resource(
                kms.Alias(
                    "Alias",
                    AliasName="%s" % key_alias,
                    TargetKeyId=Ref(key)
                )
            )

            t.add_output(Output("KeyAlias", Value=Ref(alias)))
