from troposphere.ec2 import SecurityGroupIngress, SecurityGroupEgress
from stacker.blueprints.base import Blueprint

CLASS_MAP = {
    "IngressRules": SecurityGroupIngress,
    "EgressRules": SecurityGroupEgress,
}


class Rules(Blueprint):
    """Used to add Ingress/Egress rules to existing security groups.

    This blueprint uses two variables:
        IngressRules:
            A dict with keys of the virtual titles for each rule, and with the
            value being a dict of the parameters taken directly from:
                http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-ec2-security-group-ingress.html
        EgressRules:
            A dict with keys of the virtual titles for each rule, and with the
            value being a dict of the parameters taken directly from:
                http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-security-group-egress.html

    An example:

    name: mySecurityRules
    class_path: stacker_blueprints.security_rules.Rules
    variables:
      IngressRules:
        All80ToWebserverGroup:
          CidrIp: 0.0.0.0/0
          FromPort: 80
          ToPort: 80
          GroupId: ${output WebserverStack::SecurityGroup}
          IpProtocol: tcp
    """

    VARIABLES = {
        "IngressRules": {
            "type": dict,
            "description": "A dict of ingress rules where the key is the "
                           "name of the rule to create, and the value is "
                           "a dictionary of keys/values based on the "
                           "attributes of the "
                           ":class:`troposphere.ec2.SecurityGroupIngress` "
                           "class.",
            "default": {},
        },
        "EgressRules": {
            "type": dict,
            "description": "A dict of ingress rules where the key is the "
                           "name of the rule to create, and the value is "
                           "a dictionary of keys/values based on the "
                           "attributes of the "
                           ":class:`troposphere.ec2.SecurityGroupEgress` "
                           "class.",
            "default": {},
        }
    }

    def create_security_rules(self):
        t = self.template
        variables = self.get_variables()
        for rule_type, rule_class in CLASS_MAP.items():
            for rule_title, rule_attrs in variables[rule_type].items():
                t.add_resource(rule_class.from_dict(rule_title, rule_attrs))

    def create_template(self):
        self.create_security_rules()
