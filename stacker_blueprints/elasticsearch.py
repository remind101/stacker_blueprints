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
    Policy,
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
                "The configurations of Amazon Elastic Block Store (Amazon EBS) "
                "volumes that are attached to data nodes in the Amazon ES "
                "domain"
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
                "The automated snapshot configuration for the Amazon ES domain "
                "indices."
            )},
        "Tags": {
            "type": list,
            "default": [],
            "description": (
                "An arbitrary set of tags (key-value pairs) to associate with "
                "the Amazon ES domain."
            )},
    }

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
            "AdvancedOptions": variables["AdvancedOptions"],
            "DomainName": variables["DomainName"],
            "EBSOptions": variables["EBSOptions"],
            "ElasticsearchClusterConfig": (
                variables["ElasticsearchClusterConfig"]
            ),
            "ElasticsearchVersion": variables["ElasticsearchVersion"],
            "SnapshotOptions": variables["SnapshotOptions"],
            "Tags": variables["Tags"],
        }
        domain = elasticsearch.Domain.from_dict(ES_DOMAIN, params)
        t.add_resource(domain)
        t.add_output(Output("DomainArn", Value=GetAtt(ES_DOMAIN, "DomainArn")))
        t.add_output(Output("DomainEndpoint", Value=GetAtt(ES_DOMAIN,
                                                           "DomainEndpoint")))

    def create_policy(self):
        t = self.template
        variables = self.get_variables()
        statements = [
            Statement(
                Effect=Allow,
                Action=[
                    awacs.es.Action("HttpGet"),
                    awacs.es.Action("HttpHead"),
                    awacs.es.Action("HttpPost"),
                    awacs.es.Action("HttpDelete")],
                Resource=[Join("/", [GetAtt(ES_DOMAIN, "DomainArn"), "*"])])]
        t.add_resource(
            iam.PolicyType(
                POLICY_NAME,
                PolicyName=POLICY_NAME,
                PolicyDocument=Policy(Statement=statements),
                Roles=variables["Roles"]))

    def create_template(self):
        self.create_domain()
        self.create_dns_record()
        self.create_policy()
