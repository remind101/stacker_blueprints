"""AWS Elasticsearch Service.

Blueprint to configure AWS Elasticsearch service.

Example::

    - name: elasticsearch
      class_path: stacker_blueprints.elasticsearch.Domain
      variables:
        Roles:
          - ${empireMinion::IAMRole}
        InternalZoneId: ${vpc::InternalZoneId}
        InternalZoneName: ${vpc::InternalZoneName}
        InternalHostName: es

"""
import awacs.es
from awacs.aws import (
    Allow,
    Condition,
    IpAddress,
    Policy,
    Principal,
    Everybody,
    SourceIp,
    Statement,
)
from stacker.blueprints.base import Blueprint
from troposphere import (
    elasticsearch,
    iam,
    route53,
    GetAtt,
    Join,
    Output,
    Ref,
)

ES_DOMAIN = "ESDomain"
DNS_RECORD = "ESDomainDNSRecord"
POLICY_NAME = "ESDomainAccessPolicy"


class Domain(Blueprint):

    VARIABLES = {
        "Roles": {
            "type": list,
            "description": (
                "List of roles that should have access to the ES domain.")},
        "InternalZoneId": {
            "type": str,
            "default": "",
            "description": "Internal zone id, if you have one."},
        "InternalZoneName": {
            "type": str,
            "default": "",
            "description": "Internal zone name, if you have one."},
        "InternalHostName": {
            "type": str,
            "default": "",
            "description": "Internal domain name, if you have one."},
        "AdvancedOptions": {
            "type": dict,
            "default": {},
            "description": (
                "Additional options to specify for the Amazon ES domain"
            )},
        "DomainName": {
            "type": str,
            "default": "",
            "description": "A name for the Amazon ES domain."},
        "EBSOptions": {
            "type": dict,
            "default": {},
            "description": (
                "The configurations of Amazon Elastic Block Store (Amazon "
                "EBS) volumes that are attached to data nodes in the Amazon "
                "ES domain"
            )},
        "ElasticsearchClusterConfig": {
            "type": dict,
            "default": {},
            "description": (
                "The cluster configuration for the Amazon ES domain."
            )},
        "ElasticsearchVersion": {
            "type": str,
            "default": "2.3",
            "description": "The version of Elasticsearch to use."},
        "SnapshotOptions": {
            "type": dict,
            "default": {},
            "description": (
                "The automated snapshot configuration for the Amazon ES "
                "domain indices."
            )},
        "Tags": {
            "type": list,
            "default": [],
            "description": (
                "An arbitrary set of tags (key-value pairs) to associate with "
                "the Amazon ES domain."
            )},
        "TrustedNetworks": {
            "type": list,
            "description": (
                "List of CIDR blocks allowed to connect to the ES cluster"
            ),
            "default": []},
    }

    def get_allowed_actions(self):
        return [
            awacs.es.Action("ESHttpGet"),
            awacs.es.Action("ESHttpHead"),
            awacs.es.Action("ESHttpPost"),
            awacs.es.Action("ESHttpDelete")]

    def create_dns_record(self):
        t = self.template
        variables = self.get_variables()
        should_create_dns = all([
            variables["InternalZoneId"],
            variables["InternalZoneName"],
            variables["InternalHostName"],
        ])
        if should_create_dns:
            t.add_resource(
                route53.RecordSetType(
                    DNS_RECORD,
                    HostedZoneId=variables["InternalZoneId"],
                    Comment="ES Domain CNAME Record",
                    Name="{}.{}".format(variables["InternalHostName"],
                                        variables["InternalZoneName"]),
                    Type="CNAME",
                    TTL="120",
                    ResourceRecords=[GetAtt(ES_DOMAIN, "DomainEndpoint")],
                ))
            t.add_output(Output("CNAME", Value=Ref(DNS_RECORD)))

    def create_domain(self):
        t = self.template
        variables = self.get_variables()
        params = {
            "ElasticsearchVersion": variables["ElasticsearchVersion"],
        }

        policy = self.get_access_policy()
        if policy:
            params["AccessPolicies"] = policy

        # Add any optional keys to the params dict. ES didn't have great
        # support for passing empty values for these keys when this was
        # created.
        optional_keys = ["AdvancedOptions", "DomainName", "EBSOptions",
                         "SnapshotOptions", "Tags"]

        for key in optional_keys:
            optional = variables[key]
            if optional:
                params[key] = optional

        domain = elasticsearch.Domain.from_dict(ES_DOMAIN, params)
        t.add_resource(domain)
        t.add_output(Output("DomainArn", Value=GetAtt(ES_DOMAIN, "DomainArn")))
        t.add_output(Output("DomainEndpoint", Value=GetAtt(ES_DOMAIN,
                                                           "DomainEndpoint")))

    def create_roles_policy(self):
        t = self.template
        variables = self.get_variables()
        statements = [
            Statement(
                Effect=Allow,
                Action=self.get_allowed_actions(),
                Resource=[Join("/", [GetAtt(ES_DOMAIN, "DomainArn"), "*"])])]
        t.add_resource(
            iam.PolicyType(
                POLICY_NAME,
                PolicyName=POLICY_NAME,
                PolicyDocument=Policy(Statement=statements),
                Roles=variables["Roles"]))

    def get_access_policy(self):
        policy = None
        variables = self.get_variables()

        statements = []
        for trusted_network in variables["TrustedNetworks"]:
            condition = Condition(IpAddress({SourceIp: trusted_network}))
            statements.append(
                Statement(
                    Effect=Allow,
                    Action=self.get_allowed_actions(),
                    Condition=condition,
                    Principal=Principal(Everybody)))

        if statements:
            policy = Policy(Statement=statements)
        return policy

    def create_template(self):
        self.create_domain()
        self.create_dns_record()
        self.create_roles_policy()
