import re

from troposphere import (
    Ref, ec2, Output, GetAtt, Tags
)
from troposphere.rds import (
    DBInstance, DBSubnetGroup, DBParameterGroup, OptionGroup,
)
from troposphere.route53 import RecordSetType

from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import CFNString

RDS_ENGINES = ["MySQL", "oracle-se1", "oracle-se", "oracle-ee", "sqlserver-ee",
               "sqlserver-se", "sqlserver-ex", "sqlserver-web", "postgres",
               "aurora"]

# Resource name constants
SUBNET_GROUP = "RDSSubnetGroup"
SECURITY_GROUP = "RDSSecurityGroup"
DBINSTANCE = "RDSDBInstance"
DNS_RECORD = "DBInstanceDnsRecord"


def validate_storage_type(value):
    valid_types = ["", "standard", "gp2", "io1"]
    if value not in valid_types:
        raise ValueError("Invalid storage type: %s." % value)
    return value


def validate_db_instance_identifier(value, allow_empty=True):
    if not value and allow_empty:
        # Empty value will pick up default from stackname
        return value
    pattern = r"^[a-zA-Z][a-zA-Z0-9-]*$"
    if not (0 < len(value) < 64):
        raise ValueError("Must be between 1 and 63 characters in length.")
    if not re.match(pattern, value):
        raise ValueError("Must match pattern: %s" % pattern)
    return value


def validate_db_engines(value):
    if value not in RDS_ENGINES:
        raise ValueError(
            "Engine must be one of: %s" % (", ".join(RDS_ENGINES))
        )
    return value


def validate_backup_retention_period(value):
    if not (0 <= value <= 35):
        raise ValueError(
            "Backup retention period must be between 0 and 35."
        )
    return value


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
            "type": str,
            "description": "Vpc Id"},
        "Subnets": {
            "type": str,
            "description": "A comma separated list of subnet ids."},
        "InstanceType": {
            "type": str,
            "description": "AWS RDS Instance Type",
            "default": "db.m3.large"},
        "AllowMajorVersionUpgrade": {
            "type": bool,
            "description": "Set to 'true' to allow major version "
                           "upgrades.",
            "default": False,
        },
        "AutoMinorVersionUpgrade": {
            "type": bool,
            "description": "Set to 'true' to allow minor version upgrades "
                           "during maintenance windows.",
            "default": False,
        },
        "DBFamily": {
            "type": str,
            "description": "DBFamily for ParameterGroup.",
        },
        "StorageType": {
            "type": str,
            "description": "Storage type for RDS instance. Defaults to "
                           "standard unless IOPS is set, then it "
                           "defaults to io1",
            "default": "",
            "validator": validate_storage_type,
        },
        "AllocatedStorage": {
            "type": int,
            "description": "Space, in GB, to allocate to RDS instance. If "
                           "IOPS is set below, this must be a minimum of "
                           "100 and must be at least 1/10th the IOPs "
                           "setting.",
            "default": 0
        },
        "IOPS": {
            "type": int,
            "description": "If set, uses provisioned IOPS for the "
                           "database. Note: This must be no more than "
                           "10x of AllocatedStorage. Minimum: 1000",
            "default": 0
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
        "PreferredMaintenanceWindow": {
            "type": str,
            "description": "A (minimum 30 minute) window in "
                           "DDD:HH:MM-DDD:HH:MM format in UTC for "
                           "backups. Default: Sunday 3am-4am PST",
            "default": "Sun:11:00-Sun:12:00"
        },
        "DBInstanceIdentifier": {
            "type": str,
            "description": "Name of the database instance in RDS.",
            "validator": validate_db_instance_identifier,
            "default": "",
        },
        "DBSnapshotIdentifier": {
            "type": str,
            "description": "The snapshot you want the db restored from.",
            "default": "",
        },
        "ExistingSecurityGroup": {
            "type": str,
            "description": "The ID of an existing security group to put "
                           "the RDS instance in. If not specified, one "
                           "will be created for you.",
            "default": "",
        },
        "Tags": {
            "type": dict,
            "description": "An optional dictionary of tags to put on the "
                           "database instance.",
            "default": {}
        },
    }

    def engine(self):
        return None

    def defined_variables(self):
        variables = super(BaseRDS, self).defined_variables()

        if not self.engine():
            variables['Engine'] = {
                "type": str,
                "description": "Database engine for the RDS Instance.",
                "validator": validate_db_engines,
            }
        else:
            validate_db_engines(self.engine())

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

    def get_storage_type(self):
        variables = self.get_variables()
        return variables["StorageType"] or Ref("AWS::NoValue")

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
                Family=variables["DBFamily"],
                Parameters=params,
            )
        )

    def get_option_configurations(self):
        options = []
        return options

    def create_option_group(self):
        t = self.template
        variables = self.get_variables()
        t.add_resource(
            OptionGroup(
                "OptionGroup",
                EngineName=self.engine() or variables["Engine"],
                MajorEngineVersion=variables["EngineMajorVersion"],
                OptionGroupDescription=self.name,
                OptionConfigurations=self.get_option_configurations(),
            )
        )

    def create_rds(self):
        t = self.template
        variables = self.get_variables()
        db = DBInstance(
            DBINSTANCE,
            StorageType=self.get_storage_type(),
            **self.get_common_attrs())
        # Hack till https://github.com/cloudtools/troposphere/pull/652/
        # is accepted
        if variables["IOPS"]:
            db.Iops = variables["IOPS"]
        t.add_resource(db)

    def create_dns_records(self):
        t = self.template
        variables = self.get_variables()

        # Setup CNAME to db
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
                    ResourceRecords=[self.get_db_endpoint()],
                )
            )

    def create_db_outputs(self):
        t = self.template
        t.add_output(Output("DBAddress", Value=self.get_db_endpoint()))
        t.add_output(Output("DBInstance", Value=Ref(DBINSTANCE)))
        if self.should_create_internal_hostname():
            t.add_output(
                Output(
                    "DBCname",
                    Value=Ref(DNS_RECORD)))

    def create_template(self):
        variables = self.get_variables()
        if variables.get("DBFamily"):
            self.create_parameter_group()

        if variables.get("EngineMajorVersion"):
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
                "type": int,
                "description": "Number of days to retain database backups.",
                "validator": validate_backup_retention_period,
                "default": 7,
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
            "DatabaseName": {
                "type": str,
                "description": "Initial db to create in database."
            },
            "MultiAZ": {
                "type": bool,
                "description": "Set to 'false' to disable MultiAZ support.",
                "default": True
            },
            "KmsKeyid": {
                "type": str,
                "description": "Requires that StorageEncrypted is true. "
                               "Should be an ARN to the KMS key that should "
                               "be used to encrypt the storage.",
                "default": "",
            },
            "EngineMajorVersion": {
                "type": str,
                "description": "Major Version for the engine. Basically the "
                               "first two parts of the EngineVersion you "
                               "choose."
            },
            "EngineVersion": {
                "type": str,
                "description": "Database engine version for the RDS Instance.",
            },
            "StorageEncrypted": {
                "type": bool,
                "description": "Set to 'false' to disable encrypted storage.",
                "default": True,
            },

        }
        variables.update(additional)
        return variables

    def get_common_attrs(self):
        variables = self.get_variables()
        return {
            "AllocatedStorage": variables["AllocatedStorage"],
            "AllowMajorVersionUpgrade": variables["AllowMajorVersionUpgrade"],
            "AutoMinorVersionUpgrade": variables["AutoMinorVersionUpgrade"],
            "BackupRetentionPeriod": variables["BackupRetentionPeriod"],
            "DBName": variables["DatabaseName"],
            "DBInstanceClass": variables["InstanceType"],
            "DBInstanceIdentifier": (
                variables["DBInstanceIdentifier"]
                or validate_db_instance_identifier(
                    self.context.get_fqn(self.name),
                    allow_empty=False
                )
            ),
            "DBSnapshotIdentifier": self.get_db_snapshot_identifier(),
            "DBParameterGroupName": Ref("ParameterGroup"),
            "DBSubnetGroupName": Ref(SUBNET_GROUP),
            "Engine": self.engine() or variables["Engine"],
            "EngineVersion": variables["EngineVersion"],
            # NoValue for now
            "LicenseModel": Ref("AWS::NoValue"),
            "MasterUsername": variables["MasterUser"],
            "MasterUserPassword": Ref("MasterUserPassword"),
            "MultiAZ": variables["MultiAZ"],
            "OptionGroupName": Ref("OptionGroup"),
            "PreferredBackupWindow": variables["PreferredBackupWindow"],
            "PreferredMaintenanceWindow":
                variables["PreferredMaintenanceWindow"],
            "StorageEncrypted": variables["StorageEncrypted"],
            "VPCSecurityGroups": [self.security_group, ],
            "Tags": self.get_tags(),
        }


class ReadReplica(BaseRDS):
    """Blueprint for a Read replica RDS Database Instance."""

    def defined_variables(self):
        variables = super(ReadReplica, self).defined_variables()
        additional = {
            "MasterDatabaseId": {
                "type": str,
                "description": "ID of the master database to create a read "
                               "replica of."
            },
            "EngineMajorVersion": {
                "type": str,
                "description": "Major Version for the engine. Basically the "
                               "first two parts of the EngineVersion you "
                               "choose."
            },
            "EngineVersion": {
                "type": str,
                "description": "Database engine version for the RDS Instance.",
            },
            "StorageEncrypted": {
                "type": bool,
                "description": "Set to 'false' to disable encrypted storage.",
                "default": True,
            },
        }
        variables.update(additional)
        return variables

    def get_common_attrs(self):
        variables = self.get_variables()

        return {
            "SourceDBInstanceIdentifier": variables["MasterDatabaseId"],
            "AllocatedStorage": variables["AllocatedStorage"],
            "AllowMajorVersionUpgrade": variables["AllowMajorVersionUpgrade"],
            "AutoMinorVersionUpgrade": variables["AutoMinorVersionUpgrade"],
            "DBInstanceClass": variables["InstanceType"],
            "DBInstanceIdentifier": (
                variables["DBInstanceIdentifier"]
                or validate_db_instance_identifier(
                    self.context.get_fqn(self.name),
                    allow_empty=False
                )
            ),
            "DBParameterGroupName": Ref("ParameterGroup"),
            "Engine": self.engine() or variables["Engine"],
            "EngineVersion": variables["EngineVersion"],
            "OptionGroupName": Ref("OptionGroup"),
            "PreferredMaintenanceWindow":
                variables["PreferredMaintenanceWindow"],
            "VPCSecurityGroups": [self.security_group, ],
            "Tags": self.get_tags(),
        }


class ClusterInstance(BaseRDS):
    """Blueprint for an DBCluster Instance."""

    def defined_variables(self):
        variables = super(ClusterInstance, self).defined_variables()
        variables["DBClusterIdentifier"] = {
            "type": str,
            "description": "The database cluster id to join this instance to."
        }
        return variables

    def create_subnet_group(self):
        return

    def get_common_attrs(self):
        variables = self.get_variables()

        return {
            "DBClusterIdentifier": variables["DBClusterIdentifier"],
            "AllowMajorVersionUpgrade": variables["AllowMajorVersionUpgrade"],
            "AutoMinorVersionUpgrade": variables["AutoMinorVersionUpgrade"],
            "DBInstanceClass": variables["InstanceType"],
            "DBInstanceIdentifier": (
                variables["DBInstanceIdentifier"]
                or self.context.get_fqn(self.name)
            ),
            "DBSnapshotIdentifier": self.get_db_snapshot_identifier(),
            "DBParameterGroupName": Ref("ParameterGroup"),
            "Engine": self.engine() or variables["Engine"],
            "LicenseModel": Ref("AWS::NoValue"),
            "Tags": self.get_tags(),
        }
