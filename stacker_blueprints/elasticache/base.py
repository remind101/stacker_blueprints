from troposphere import (
    Ref, ec2, Output, GetAtt, Join
)

from troposphere.elasticache import (
    ReplicationGroup, ParameterGroup, SubnetGroup
)

from troposphere.route53 import RecordSetType

from stacker.blueprints.base import Blueprint

# Resource name constants
SUBNET_GROUP = "SubnetGroup"
SECURITY_GROUP = "SecurityGroup"
REPLICATION_GROUP = "ReplicationGroup"
DNS_RECORD = "ReplicationGroupDnsRecord"
PARAMETER_GROUP = "ParameterGroup"

NOVALUE = Ref("AWS::NoValue")


class BaseReplicationGroup(Blueprint):
    """Base Blueprint for all Elasticache ReplicationGroup blueprints.

    ReplicationGroups are only currently supported by the redis engine.
    """

    ALLOWED_ENGINES = ["redis"]

    VARIABLES = {
        "ClusterParameters": {
            "type": dict,
            "default": {},
        },
        "VpcId": {
            "type": str,
            "description": "Vpc Id to place the Cluster in"
        },
        "Subnets": {
            "type": str,
            "description": "Comma separated list of subnets to deploy the "
                           "Cluster nodes in."
        },
        "AutomaticFailoverEnabled": {
            "type": bool,
            "description": "Specifies whether a read-only replica will be "
                           "automatically promoted to read/write primary "
                           "if the existing primary fails. If true, "
                           "Multi-AZ is enabled for this replication "
                           "group. If false, Multi-AZ is disabled for "
                           "this replication group. If true, "
                           "NumCacheClusters must be at least 2.",
            "default": True,
        },
        "AutoMinorVersionUpgrade": {
            "type": bool,
            "description": "Set to 'true' to allow minor version upgrades "
                           "during maintenance windows.",
        },
        "CacheNodeType": {
            "type": str,
            "description": "AWS ElastiCache Cache Node Type",
        },
        "EngineVersion": {
            "type": str,
            "description": "Engine version for the Cache Cluster.",
        },
        "NotificationTopicArn": {
            "type": str,
            "description": "ARN of the SNS Topic to publish events to.",
            "default": "",
        },
        "NumCacheClusters": {
            "type": int,
            "description": "The number of cache clusters this replication "
                           "group will initially have. If Multi-AZ "
                           "(ie: the AutomaticFailoverEnabled Parameter) "
                           "is enabled, the value of this parameter must "
                           "be at least 2.",
            "default": 2,
        },
        "Port": {
            "type": int,
            "description": "The port to run the cluster on.",
            "default": 0,
        },
        "PreferredCacheClusterAZs": {
            "type": list,
            "description": "Must match the # of nodes in "
                           "NumCacheClusters.",
            "default": [],
        },
        "PreferredMaintenanceWindow": {
            "type": str,
            "description": "A (minimum 60 minute) window in "
                           "DDD:HH:MM-DDD:HH:MM format in UTC for "
                           "backups. Default: Sunday 3am-4am PST",
            "default": "Sun:11:00-Sun:12:00"
        },
        "SnapshotArns": {
            "type": list,
            "description": "A list of s3 ARNS where redis snapshots are "
                           "stored that will be used to create the "
                           "cluster.",
            "default": [],
        },
        "SnapshotRetentionLimit": {
            "type": int,
            "description": "The number of daily snapshots to retain. Only "
                           "valid for clusters with the redis Engine.",
            "default": 0,
        },
        "SnapshotWindow": {
            "type": str,
            "description": "For Redis cache clusters, daily time range "
                           "(in UTC) during which ElastiCache will begin "
                           "taking a daily snapshot of your node group. "
                           "For example, you can specify 05:00-09:00.",
            "default": ""
        },
        "InternalZoneId": {
            "type": str,
            "description": "Internal zone Id, if you have one.",
            "default": "",
        },
        "InternalZoneName": {
            "type": str,
            "description": "Internal zone name, if you have one.",
            "default": "",
        },
        "InternalHostname": {
            "type": str,
            "description": "Internal domain name, if you have one.",
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

    def get_parameter_group_family(self):
        """Used by engine specific subclasses to return parameter group family.

        Should only be overridden if the class variable ENGINE is defined on
        the class.

        Return:
            list: A list of valid parameter group families for the given
                  engine.
        """
        return []

    def defined_variables(self):
        variables = super(BaseReplicationGroup, self).defined_variables()
        variables["ParameterGroupFamily"] = {
            "type": str,
            "description": "The parametergroup family to use, dependent "
                           "on the engine.",
            "allowed_values": self.get_parameter_group_family()
        }
        engine_versions = self.get_engine_versions()
        if engine_versions:
            variables['EngineVersion']['allowed_values'] = engine_versions

        if self.engine() not in self.ALLOWED_ENGINES:
            raise ValueError("ENGINE must be one of: %s" %
                             ", ".join(self.ALLOWED_ENGINES))

        return variables

    def create_parameter_group(self):
        t = self.template
        variables = self.get_variables()
        params = variables["ClusterParameters"]
        t.add_resource(
            ParameterGroup(
                PARAMETER_GROUP,
                Description=self.name,
                CacheParameterGroupFamily=variables["ParameterGroupFamily"],
                Properties=params,
            )
        )

    def create_subnet_group(self):
        t = self.template
        t.add_resource(
            SubnetGroup(
                SUBNET_GROUP,
                Description="%s subnet group." % self.name,
                SubnetIds=self.get_variables()["Subnets"].split(',')))

    def create_security_group(self):
        t = self.template
        sg = t.add_resource(
            ec2.SecurityGroup(
                SECURITY_GROUP,
                GroupDescription="%s security group" % self.name,
                VpcId=self.get_variables()["VpcId"]))
        t.add_output(Output("SecurityGroup", Value=Ref(sg)))

    def create_replication_group(self):
        t = self.template
        variables = self.get_variables()
        availability_zones = variables["PreferredCacheClusterAZs"] or NOVALUE
        notification_topic_arn = variables["NotificationTopicArn"] or \
            NOVALUE
        port = variables["Port"] or NOVALUE
        snapshot_arns = variables["SnapshotArns"] or NOVALUE
        snapshot_retention_limit = variables["SnapshotRetentionLimit"] or \
            NOVALUE
        snapshot_window = variables["SnapshotWindow"] or NOVALUE
        maintenance_window = variables["PreferredMaintenanceWindow"] or \
            NOVALUE

        t.add_resource(
            ReplicationGroup(
                REPLICATION_GROUP,
                AutomaticFailoverEnabled=variables["AutomaticFailoverEnabled"],
                AutoMinorVersionUpgrade=variables["AutoMinorVersionUpgrade"],
                CacheNodeType=variables["CacheNodeType"],
                CacheParameterGroupName=Ref(PARAMETER_GROUP),
                CacheSubnetGroupName=Ref(SUBNET_GROUP),
                NumCacheClusters=variables["NumCacheClusters"],
                Engine=self.engine(),
                EngineVersion=variables["EngineVersion"],
                NotificationTopicArn=notification_topic_arn,
                Port=port,
                PreferredCacheClusterAZs=availability_zones,
                PreferredMaintenanceWindow=maintenance_window,
                ReplicationGroupDescription=self.name,
                SecurityGroupIds=[Ref(SECURITY_GROUP), ],
                SnapshotArns=snapshot_arns,
                SnapshotRetentionLimit=snapshot_retention_limit,
                SnapshotWindow=snapshot_window,
            )
        )

    def get_primary_address(self):
        return GetAtt(REPLICATION_GROUP, "PrimaryEndPoint.Address")

    def get_secondary_addresses(self):
        return GetAtt(REPLICATION_GROUP, "ReadEndPoint.Addresses.List")

    def should_create_internal_cname(self):
        variables = self.get_variables()
        return all([variables["InternalZoneId"],
                    variables["InternalZoneName"],
                    variables["InternalHostname"]])

    def create_dns_records(self):
        t = self.template
        variables = self.get_variables()
        primary_endpoint = self.get_primary_address()

        if self.should_create_internal_cname():
            t.add_resource(
                RecordSetType(
                    DNS_RECORD,
                    HostedZoneId=variables["InternalZoneId"],
                    Comment="ReplicationGroup CNAME Record",
                    Name=Join(".", [variables["InternalHostname"],
                              variables["InternalZoneName"]]),
                    Type="CNAME",
                    TTL="120",
                    ResourceRecords=[primary_endpoint]))

    def create_cluster_outputs(self):
        t = self.template
        t.add_output(Output("PrimaryAddress",
                            Value=self.get_primary_address()))
        t.add_output(Output("ReadAddresses",
                            Value=Join(",", self.get_secondary_addresses())))

        t.add_output(Output("ClusterPort",
                            Value=GetAtt(REPLICATION_GROUP,
                                         "PrimaryEndPoint.Port")))
        t.add_output(Output("ClusterId", Value=Ref(REPLICATION_GROUP)))
        if self.should_create_internal_cname():
            t.add_output(
                Output(
                    "PrimaryCname",
                    Value=Ref(DNS_RECORD)))

    def create_template(self):
        self.create_parameter_group()
        self.create_subnet_group()
        self.create_security_group()
        self.create_replication_group()
        self.create_dns_records()
        self.create_cluster_outputs()
