from troposphere import (
    Ref, ec2, Output, GetAtt, Not, Equals, Condition, And, Join, If, Tags
)
from troposphere.rds import (
    DBInstance, DBSubnetGroup, DBParameterGroup, OptionGroup,
)
from troposphere.route53 import RecordSetType

from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import (
    CFNNumber,
    CFNString,
    EC2SubnetIdList,
    EC2VPCId,
)

RDS_ENGINES = ["MySQL", "oracle-se1", "oracle-se", "oracle-ee", "sqlserver-ee",
               "sqlserver-se", "sqlserver-ex", "sqlserver-web", "postgres"]

# Resource name constants
SUBNET_GROUP = "RDSSubnetGroup"
SECURITY_GROUP = "RDSSecurityGroup"
DBINSTANCE = "RDSDBInstance"
DNS_RECORD = "DBInstanceDnsRecord"


class BaseRDS(Blueprint):
    """Base Blueprint for all RDS blueprints.

    Should not be used directly. Either use :class:`MasterInstance` or
    :class:`ReadReplica` classes, or a engine specific blueprint like
    :class:`stacker.blueprints.rds.postgres.MasterInstance` or
    :class:`stacker.blueprints.rds.postgres.ReadReplica`.
    """

    VARIABLES = {
        "DatabaseParameters": {
            "type": dict,
            "default": {},
        },
        "VpcId": {
            "type": EC2VPCId,
            "description": "Vpc Id"},
        "Subnets": {
            "type": EC2SubnetIdList,
            "description": "Subnets to deploy RDS instance in."},
        "InstanceType": {
            "type": CFNString,
            "description": "AWS RDS Instance Type",
            "default": "db.m3.large"},
        "AllowMajorVersionUpgrade": {
            "type": CFNString,
            "description": "Set to 'true' to allow major version "
                           "upgrades.",
            "default": "false",
            "allowed_values": ["true", "false"]
        },
        "AutoMinorVersionUpgrade": {
            "type": CFNString,
            "description": "Set to 'true' to allow minor version upgrades "
                           "during maintenance windows.",
            "default": "false",
            "allowed_values": ["true", "false"]
        },
        "StorageType": {
            "type": CFNString,
            "description": "Storage type for RDS instance. Defaults to "
                           "standard unless IOPS is set, then it "
                           "defaults to io1",
            "default": "default",
            "allowed_values": ["default", "standard", "gp2", "io1"]
        },
        "AllocatedStorage": {
            "type": CFNNumber,
            "description": "Space, in GB, to allocate to RDS instance. If "
                           "IOPS is set below, this must be a minimum of "
                           "100 and must be at least 1/10th the IOPs "
                           "setting.",
            "default": "10"},
        "IOPS": {
            "type": CFNNumber,
            "description": "If set, uses provisioned IOPS for the "
                           "database. Note: This must be no more than "
                           "10x of AllocatedStorage. Minimum: 1000",
            "max_value": "10000",
            "default": "0"},
        "InternalZoneId": {
            "type": CFNString,
            "default": "",
            "description": "Internal zone Id, if you have one."},
        "InternalZoneName": {
            "type": CFNString,
            "default": "",
            "description": "Internal zone name, if you have one."},
        "InternalHostname": {
            "type": CFNString,
            "default": "",
            "description": "Internal domain name, if you have one."},
        "PreferredMaintenanceWindow": {
            "type": CFNString,
            "description": "A (minimum 30 minute) window in "
                           "DDD:HH:MM-DDD:HH:MM format in UTC for "
                           "backups. Default: Sunday 3am-4am PST",
            "default": "Sun:11:00-Sun:12:00"},
        "DBSnapshotIdentifier": {
            "type": CFNString,
            "description": "The snapshot you want the db restored from.",
            "default": "",
        },
        "EngineVersion": {
            "type": CFNString,
            "description": "Database engine version for the RDS Instance.",
        },
        "EngineMajorVersion": {
            "type": CFNString,
            "description": "Major Version for the engine. Basically the "
                           "first two parts of the EngineVersion you "
                           "choose."
        },
        "StorageEncrypted": {
            "type": CFNString,
            "description": "Set to 'false' to disable encrypted storage.",
            "default": "true",
            "allowed_values": ["true", "false"]
        },
        "ExistingSecurityGroup": {
            "type": CFNString,
            "description": "The ID of an existing security group to put "
                           "the RDS instance in. If not specified, one "
                           "will be created for you.",
            "default": "",
        },
    }

    def engine(self):
        return None

    def get_engine_versions(self):
        """Used by engine specific subclasses - returns valid engine versions.

        Should only be overridden if the class variable ENGINE is defined on
        the class.

        Return:
            list: A list of valid engine versions for the given engine.
        """
        return []

    def get_engine_major_versions(self):
        """Used by engine specific subclasses. Returns major engine versions.

        By default will attempt to figure out the right thing to return by
        returning a list of the first two parts of each version returned by
        get_engine_versions.

        Return:
            list: A list of valid engine versions for the given engine.
        """
        versions = self.get_engine_versions()
        major_versions = []
        for v in versions:
            parts = v.split('.')
            major_versions.append(".".join(parts[:2]))
        return major_versions

    def get_db_families(self):
        """Returns available db families.

        Should be overridden by engine specific subclasses to be more
        specific.

        Return:
            list: A list of valid db families for a given db engine.
        """
        return [
            "mysql5.1", "mysql5.5", "mysql5.6", "mysql5.7",
            "oracle-ee-11.2", "oracle-ee-12.1",
            "oracle-se-11.2", "oracle-se-12.1",
            "oracle-se1-11.2", "oracle-se1-12.1",
            "postgres9.3", "postgres9.4", "postgres9.5",
            "sqlserver-ee-10.50", "sqlserver-ee-11.00",
            "sqlserver-ex-10.50", "sqlserver-ex-11.00",
            "sqlserver-se-10.50", "sqlserver-se-11.00",
            "sqlserver-web-10.50", "sqlserver-web-11.00"
        ]

    def defined_variables(self):
        variables = super(BaseRDS, self).defined_variables()
        variables["DBFamily"] = {
            "type": CFNString,
            "description": "DBFamily for ParameterGroup.",
            "allowed_values": self.get_db_families()}

        variables["DBInstanceIdentifier"] = {
            "type": CFNString,
            "description": "Name of the database instance in RDS.",
            "min_length": "1",
            "max_length": "63",
            "allowed_pattern": "[a-zA-Z][a-zA-Z0-9-]*",
            "default": self.name}

        engine_versions = self.get_engine_versions()
        if engine_versions:
            variables['EngineVersion']['allowed_values'] = engine_versions

        engine_major_versions = self.get_engine_major_versions()
        if engine_major_versions:
            variables['EngineMajorVersion']['allowed_values'] = \
                engine_major_versions

        if not self.engine():
            variables['Engine'] = {
                "type": CFNString,
                "description": "Database engine for the RDS Instance.",
                "allowed_values": RDS_ENGINES
            }
        else:
            if self.engine() not in RDS_ENGINES:
                raise ValueError("ENGINE must be one of: %s" %
                                 ", ".join(RDS_ENGINES))

        return variables

    def create_conditions(self):
        t = self.template
        t.add_condition(
            "HasInternalZone",
            Not(Equals(Ref("InternalZoneId"), "")))
        t.add_condition(
            "HasInternalZoneName",
            Not(Equals(Ref("InternalZoneName"), "")))
        t.add_condition(
            "HasInternalHostname",
            Not(Equals(Ref("InternalHostname"), "")))
        t.add_condition(
            "CreateInternalHostname",
            And(Condition("HasInternalZone"),
                Condition("HasInternalZoneName"),
                Condition("HasInternalHostname")))
        t.add_condition(
            "HasProvisionedIOPS",
            Not(Equals(Ref("IOPS"), "0")))
        t.add_condition(
            "HasStorageType",
            Not(Equals(Ref("StorageType"), "default")))
        t.add_condition(
            "HasDBSnapshotIdentifier",
            Not(Equals(Ref("DBSnapshotIdentifier"), "")))
        t.add_condition(
            "CreateSecurityGroup",
            Equals(Ref("ExistingSecurityGroup"), "")
        )

    def create_subnet_group(self):
        t = self.template
        t.add_resource(
            DBSubnetGroup(
                SUBNET_GROUP,
                DBSubnetGroupDescription="%s VPC subnet group." % self.name,
                SubnetIds=Ref("Subnets")))

    def create_security_group(self):
        t = self.template
        sg = t.add_resource(
            ec2.SecurityGroup(
                SECURITY_GROUP,
                Condition="CreateSecurityGroup",
                GroupDescription="%s RDS security group" % self.name,
                VpcId=Ref("VpcId")))
        self.security_group = If(
            "CreateSecurityGroup",
            Ref(sg),
            Ref("ExistingSecurityGroup")
        )
        t.add_output(Output("SecurityGroup", Value=self.security_group))

    def get_db_endpoint(self):
        endpoint = GetAtt(DBINSTANCE, "Endpoint.Address")
        return endpoint

    def create_parameter_group(self):
        t = self.template
        variables = self.get_variables()
        params = variables["DatabaseParameters"]
        t.add_resource(
            DBParameterGroup(
                "ParameterGroup",
                Description=self.name,
                Family=Ref("DBFamily"),
                Parameters=params,
            )
        )

    def get_option_configurations(self):
        options = []
        return options

    def create_option_group(self):
        t = self.template
        t.add_resource(
            OptionGroup(
                "OptionGroup",
                EngineName=self.engine() or Ref("Engine"),
                MajorEngineVersion=Ref("EngineMajorVersion"),
                OptionGroupDescription=self.name,
                OptionConfigurations=self.get_option_configurations(),
            )
        )

    def create_rds(self):
        t = self.template
        t.add_resource(
            DBInstance(
                DBINSTANCE,
                StorageType=If("HasStorageType",
                               Ref("StorageType"),
                               Ref("AWS::NoValue")),
                Iops=If("HasProvisionedIOPS",
                        Ref("IOPS"),
                        Ref("AWS::NoValue")),
                **self.get_common_attrs()))

    def create_dns_records(self):
        t = self.template
        endpoint = self.get_db_endpoint()

        # Setup CNAME to db
        t.add_resource(
            RecordSetType(
                DNS_RECORD,
                # Appends a "." to the end of the domain
                HostedZoneId=Ref("InternalZoneId"),
                Comment="RDS DB CNAME Record",
                Name=Join(".", [Ref("InternalHostname"),
                          Ref("InternalZoneName")]),
                Type="CNAME",
                TTL="120",
                ResourceRecords=[endpoint],
                Condition="CreateInternalHostname"))

    def create_db_outputs(self):
        t = self.template
        t.add_output(Output("DBAddress", Value=self.get_db_endpoint()))
        t.add_output(Output("DBInstance", Value=Ref(DBINSTANCE)))
        t.add_output(
            Output(
                "DBCname",
                Condition="CreateInternalHostname",
                Value=Ref(DNS_RECORD)))

    def create_template(self):
        self.create_conditions()
        self.create_parameter_group()
        self.create_option_group()
        self.create_subnet_group()
        self.create_security_group()
        self.create_rds()
        self.create_dns_records()
        self.create_db_outputs()


class MasterInstance(BaseRDS):
    """Blueprint for a generic Master RDS Database Instance.

    Subclasses should be created for each RDS engine for better validation of
    things like engine version.
    """

    def defined_variables(self):
        variables = super(MasterInstance, self).defined_variables()
        additional = {
            "BackupRetentionPeriod": {
                "type": CFNNumber,
                "description": "Number of days to retain database backups.",
                "min_value": "0",
                "default": "7",
                "max_value": "35",
                "constraint_description": "Must be between 0-35.",
            },
            "MasterUser": {
                "type": CFNString,
                "description": "Name of the master user in the db.",
                "default": "dbuser"},
            "MasterUserPassword": {
                "type": CFNString,
                "no_echo": True,
                "description": "Master user password."},
            "PreferredBackupWindow": {
                "type": CFNString,
                "description": "A (minimum 30 minute) window in HH:MM-HH:MM "
                               "format in UTC for backups. Default: 4am-5am "
                               "PST",
                "default": "12:00-13:00"},
            "DatabaseName": {
                "type": CFNString,
                "description": "Initial db to create in database."},
            "MultiAZ": {
                "type": CFNString,
                "description": "Set to 'false' to disable MultiAZ support.",
                "default": "true"},
            "KmsKeyid": {
                "type": CFNString,
                "description": "Requires that StorageEncrypted is true. "
                               "Should be an ARN to the KMS key that should "
                               "be used to encrypt the storage.",
                "default": "",
            },
        }
        variables.update(additional)
        return variables

    def get_common_attrs(self):
        return {
            "AllocatedStorage": Ref("AllocatedStorage"),
            "AllowMajorVersionUpgrade": Ref("AllowMajorVersionUpgrade"),
            "AutoMinorVersionUpgrade": Ref("AutoMinorVersionUpgrade"),
            "BackupRetentionPeriod": Ref("BackupRetentionPeriod"),
            "DBName": Ref("DatabaseName"),
            "DBInstanceClass": Ref("InstanceType"),
            "DBInstanceIdentifier": Ref("DBInstanceIdentifier"),
            "DBSnapshotIdentifier": If(
                "HasDBSnapshotIdentifier",
                Ref("DBSnapshotIdentifier"),
                Ref("AWS::NoValue"),
            ),
            "DBParameterGroupName": Ref("ParameterGroup"),
            "DBSubnetGroupName": Ref(SUBNET_GROUP),
            "Engine": self.engine() or Ref("Engine"),
            "EngineVersion": Ref("EngineVersion"),
            # NoValue for now
            "LicenseModel": Ref("AWS::NoValue"),
            "MasterUsername": Ref("MasterUser"),
            "MasterUserPassword": Ref("MasterUserPassword"),
            "MultiAZ": Ref("MultiAZ"),
            "OptionGroupName": Ref("OptionGroup"),
            "PreferredBackupWindow": Ref("PreferredBackupWindow"),
            "PreferredMaintenanceWindow": Ref("PreferredMaintenanceWindow"),
            "StorageEncrypted": Ref("StorageEncrypted"),
            "VPCSecurityGroups": [self.security_group, ],
            "Tags": Tags(Name=self.name),
        }


class ReadReplica(BaseRDS):
    """Blueprint for a Read replica RDS Database Instance."""

    def defined_variables(self):
        variables = super(ReadReplica, self).defined_variables()
        variables['MasterDatabaseId'] = {
            "type": CFNString,
            "description": "ID of the master database to create a read "
                           "replica of."}
        return variables

    def get_common_attrs(self):
        return {
            "SourceDBInstanceIdentifier": Ref("MasterDatabaseId"),
            "AllocatedStorage": Ref("AllocatedStorage"),
            "AllowMajorVersionUpgrade": Ref("AllowMajorVersionUpgrade"),
            "AutoMinorVersionUpgrade": Ref("AutoMinorVersionUpgrade"),
            "DBInstanceClass": Ref("InstanceType"),
            "DBInstanceIdentifier": Ref("DBInstanceIdentifier"),
            "DBParameterGroupName": Ref("ParameterGroup"),
            "Engine": self.engine() or Ref("Engine"),
            "EngineVersion": Ref("EngineVersion"),
            "OptionGroupName": Ref("OptionGroup"),
            "PreferredMaintenanceWindow": Ref("PreferredMaintenanceWindow"),
            "VPCSecurityGroups": [self.security_group, ],
        }
