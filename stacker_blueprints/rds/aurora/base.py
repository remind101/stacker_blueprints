from troposphere import (
    GetAtt, Ref, ec2, Output, Tags
)
from troposphere.rds import (
    DBSubnetGroup,
    DBClusterParameterGroup,
    DBCluster,
)
from troposphere.route53 import RecordSetType

from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import CFNString

from stacker_blueprints.rds.base import validate_backup_retention_period

# Resource name constants
SUBNET_GROUP = "SubnetGroup"
PARAMETER_GROUP = "ClusterParameterGroup"
SECURITY_GROUP = "SecurityGroup"
DBCLUSTER = "DBCluster"
DNS_RECORD = "DBClusterMasterDnsRecord"


class Cluster(Blueprint):
    VARIABLES = {
        "BackupRetentionPeriod": {
            "type": int,
            "description": "Number of days to retain database backups.",
            "validator": validate_backup_retention_period,
            "default": 7,
        },
        "DatabaseName": {
            "type": str,
            "description": "Initial db to create in database."
        },
        "DBFamily": {
            "type": str,
            "description": "DBFamily for ParameterGroup.",
        },
        "ClusterParameters": {
            "type": dict,
            "description": "A dictionary of parameters to apply to the "
                           "cluster.",
            "default": {},
        },
        "VpcId": {
            "type": str,
            "description": "Vpc Id"
        },
        "Subnets": {
            "type": str,
            "description": "A comma separated list of subnet ids."
        },

        "EngineVersion": {
            "type": str,
            "description": "Database engine version for the RDS Instance.",
        },
        "MasterUser": {
            "type": str,
            "description": "Name of the master user in the db.",
        },
        "MasterUserPassword": {
            "type": CFNString,
            "no_echo": True,
            "description": "Master user password."
        },
        "PreferredBackupWindow": {
            "type": str,
            "description": "A (minimum 30 minute) window in HH:MM-HH:MM "
                           "format in UTC for backups. Default: 4am-5am "
                           "PST",
            "default": "12:00-13:00"
        },
        "PreferredMaintenanceWindow": {
            "type": str,
            "description": "A (minimum 30 minute) window in "
                           "DDD:HH:MM-DDD:HH:MM format in UTC for "
                           "backups. Default: Sunday 3am-4am PST",
            "default": "Sun:11:00-Sun:12:00"
        },
        "SnapshotIdentifier": {
            "type": str,
            "description": "The snapshot you want the db restored from.",
            "default": "",
        },
        "StorageEncrypted": {
            "type": bool,
            "description": "Set to 'false' to disable encrypted storage.",
            "default": True,
        },
        "Tags": {
            "type": dict,
            "description": "An optional dictionary of tags to put on the "
                           "database instance.",
            "default": {}
        },
        "ExistingSecurityGroup": {
            "type": str,
            "description": "The ID of an existing security group to put "
                           "the RDS instance in. If not specified, one "
                           "will be created for you.",
            "default": "",
        },
        "InternalZoneId": {
            "type": str,
            "default": "",
            "description": "Internal zone Id, if you have one."
        },
        "InternalZoneName": {
            "type": str,
            "default": "",
            "description": "Internal zone name, if you have one."
        },
        "InternalHostname": {
            "type": str,
            "default": "",
            "description": "Internal domain name, if you have one."
        },
    }

    def engine(self):
        return None

    def defined_variables(self):
        variables = super(Cluster, self).defined_variables()

        if not self.engine():
            variables['Engine'] = {
                "type": str,
                "description": "Database engine for the Aurora Cluster.",
            }

        return variables

    def should_create_internal_hostname(self):
        variables = self.get_variables()
        return all(
            [
                variables["InternalZoneId"],
                variables["InternalZoneName"],
                variables["InternalHostname"]
            ]
        )

    def get_db_snapshot_identifier(self):
        variables = self.get_variables()
        return variables["DBSnapshotIdentifier"] or Ref("AWS::NoValue")

    def get_tags(self):
        variables = self.get_variables()
        tag_var = variables["Tags"]
        t = {"Name": self.name}
        t.update(tag_var)
        return Tags(**t)

    def create_subnet_group(self):
        t = self.template
        variables = self.get_variables()
        t.add_resource(
            DBSubnetGroup(
                SUBNET_GROUP,
                DBSubnetGroupDescription="%s VPC subnet group." % self.name,
                SubnetIds=variables["Subnets"].split(",")
            )
        )
        t.add_output(Output("SubnetGroup", Value=Ref(SUBNET_GROUP)))

    def create_security_group(self):
        t = self.template
        variables = self.get_variables()
        self.security_group = variables["ExistingSecurityGroup"]
        if not variables["ExistingSecurityGroup"]:
            sg = t.add_resource(
                ec2.SecurityGroup(
                    SECURITY_GROUP,
                    GroupDescription="%s RDS security group" % self.name,
                    VpcId=variables["VpcId"]
                )
            )
            self.security_group = Ref(sg)
        t.add_output(Output("SecurityGroup", Value=self.security_group))

    def get_master_endpoint(self):
        endpoint = GetAtt(DBCLUSTER, "Endpoint.Address")
        return endpoint

    def create_parameter_group(self):
        t = self.template
        variables = self.get_variables()
        params = variables["ClusterParameters"]
        if params:
            t.add_resource(
                DBClusterParameterGroup(
                    PARAMETER_GROUP,
                    Description=self.name,
                    Family=variables["DBFamily"],
                    Parameters=params,
                )
            )

    def create_cluster(self):
        t = self.template
        variables = self.get_variables()
        parameter_group = Ref("AWS::NoValue")
        if variables["ClusterParameters"]:
            parameter_group = Ref(PARAMETER_GROUP)

        t.add_resource(
            DBCluster(
                DBCLUSTER,
                BackupRetentionPeriod=variables["BackupRetentionPeriod"],
                DBClusterParameterGroupName=parameter_group,
                DBSubnetGroupName=Ref(SUBNET_GROUP),
                Engine=self.engine() or variables["Engine"],
                EngineVersion=variables["EngineVersion"],
                MasterUsername=variables["MasterUser"],
                MasterUserPassword=Ref("MasterUserPassword"),
                PreferredBackupWindow=variables["PreferredBackupWindow"],
                PreferredMaintenanceWindow=variables[
                    "PreferredMaintenanceWindow"],
                Tags=self.get_tags(),
                VpcSecurityGroupIds=[self.security_group, ]
            )
        )

    def create_dns_records(self):
        t = self.template
        variables = self.get_variables()

        # Setup CNAME to cluster
        if self.should_create_internal_hostname():
            hostname = "%s.%s" % (
                variables["InternalHostname"],
                variables["InternalZoneName"]
            )
            t.add_resource(
                RecordSetType(
                    DNS_RECORD,
                    # Appends a "." to the end of the domain
                    HostedZoneId=variables["InternalZoneId"],
                    Comment="RDS DB CNAME Record",
                    Name=hostname,
                    Type="CNAME",
                    TTL="120",
                    ResourceRecords=[self.get_master_endpoint()],
                )
            )

    def create_outputs(self):
        t = self.template
        t.add_output(
            Output("MasterEndpoint", Value=self.get_master_endpoint())
        )
        t.add_output(Output("Cluster", Value=Ref(DBCLUSTER)))
        if self.should_create_internal_hostname():
            t.add_output(
                Output("DBCname", Value=Ref(DNS_RECORD))
            )

    def create_template(self):
        self.create_subnet_group()
        self.create_security_group()
        self.create_parameter_group()
        self.create_cluster()
        self.create_dns_records()
        self.create_outputs()


class AuroraCluster(Cluster):
    def engine(self):
        return "aurora"
