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


class Domain(Base):

    VARIABLES = {
        "Roles": {
            "type": list,
            "description": (
                "List of roles that should have access to the ES domain.")},
        "InternalZoneId": {
            "type": str,
            "default": None,
            "description": "Internal zone id, if you have one."},
        "InternalZoneName": {
            "type": str,
            "default": None,
            "description": "Internal zone name, if you have one."},
        "InternalHostName": {
            "type": str,
            "default": None,
            "description": "Internal domain name, if you have one."},
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
        t.add_resource(elasticsearch.ElasticsearchDomain(ES_DOMAIN))
        t.add_output(Output("DomainArn", Value=GetAtt(ES_DOMAIN, "DomainArn")))
        t.add_output(Output("DomainEndpoint", Value=GetAtt(ES_DOMAIN,
                                                           "DomainEndpoint")))

    def create_policy(self):
        variables = self.get-variables()
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
