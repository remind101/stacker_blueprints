""" The 'base' cloudformation stack that builds out the virtual datacenter.

This includes the VPC, it's subnets, availability zones, etc.
"""

from troposphere import (
    Ref, Output, Join, FindInMap, Select, GetAZs, Tags,
    GetAtt
)
from troposphere import ec2
from troposphere.route53 import HostedZone, HostedZoneVPCs

from stacker.blueprints.base import Blueprint

NAT_INSTANCE_NAME = 'NatInstance%s'
NAT_GATEWAY_NAME = 'NatGateway%s'
GATEWAY = 'InternetGateway'
GW_ATTACH = 'GatewayAttach'
VPC_NAME = "VPC"
VPC_ID = Ref(VPC_NAME)
DEFAULT_SG = "DefaultSG"
NAT_SG = "NATSG"

NOVALUE = Ref("AWS::NoValue")


class VPC(Blueprint):
    VARIABLES = {
        "AZCount": {
            "type": int,
            "default": 2,
        },
        "PrivateSubnets": {
            "type": list,
            "description": "List of subnets to use for non-public hosts. "
                           "NOTE: Must have as many subnets as AZCount"},
        "PublicSubnets": {
            "type": list,
            "description": "List of subnets to use for public hosts. NOTE: "
                           "Must have as many subnets as AZCount"},
        "BaseDomain": {
            "type": str,
            "default": "",
            "description": "Base domain for the stack."},
        "InternalDomain": {
            "type": str,
            "default": "",
            "description": "Internal domain name, if you have one."},
        "CidrBlock": {
            "type": str,
            "description": "Base CIDR block for subnets.",
            "default": "10.128.0.0/16"},
        "UseNatGateway": {
            "type": bool,
            "description": "If set to false, will configure NAT Instances"
                           "instead of NAT gateways.",
            "default": True},
        "ImageName": {
            "type": str,
            "description": "The image name to use from the AMIMap (usually "
                           "found in the config file.)",
            "default": "NAT"},
        "InstanceType": {
            "type": str,
            "description": "If using NAT Instances, the instance type to use.",
            "default": "m3.medium"},
        "SshKeyName": {
            "type": str,
            "description": "If using NAT Instances, the SSH key to install "
                           "on those instances.",
            "default": ""},
    }

    def create_vpc(self):
        t = self.template
        t.add_resource(ec2.VPC(
            VPC_NAME,
            CidrBlock=self.get_variables()["CidrBlock"], EnableDnsSupport=True,
            EnableDnsHostnames=True))

        # Just about everything needs this, so storing it on the object
        t.add_output(Output("VpcId", Value=VPC_ID))

    def create_internal_zone(self):
        t = self.template
        variables = self.get_variables()

        if variables["InternalDomain"]:
            t.add_resource(
                HostedZone(
                    "InternalZone",
                    Name=variables["InternalDomain"],
                    VPCs=[HostedZoneVPCs(
                        VPCId=VPC_ID,
                        VPCRegion=Ref("AWS::Region"))]
                )
            )
            t.add_output(
                Output(
                    "InternalZoneId",
                    Value=Ref("InternalZone"),
                )
            )
            t.add_output(
                Output(
                    "InternalZoneName",
                    Value=variables["InternalDomain"],
                )
            )

    def create_default_security_group(self):
        t = self.template
        t.add_resource(
            ec2.SecurityGroup(
                DEFAULT_SG,
                VpcId=VPC_ID,
                GroupDescription='Default Security Group'
            )
        )
        t.add_output(
            Output(
                'DefaultSG',
                Value=Ref(DEFAULT_SG)
            )
        )

    def has_hosted_zones(self):
        variables = self.get_variables()
        return any([
            variables["BaseDomain"],
            variables["InternalDomain"]
        ])

    def create_dhcp_options(self):
        t = self.template
        variables = self.get_variables()
        domain_name = Join(
            " ",
            [
                variables["InternalDomain"],
                variables["BaseDomain"]
            ]
        )
        if self.has_hosted_zones():
            dhcp_options = t.add_resource(
                ec2.DHCPOptions(
                    'DHCPOptions',
                    DomainName=domain_name,
                    DomainNameServers=['AmazonProvidedDNS', ],
                )
            )
            t.add_resource(
                ec2.VPCDHCPOptionsAssociation(
                    'DHCPAssociation',
                    VpcId=VPC_ID,
                    DhcpOptionsId=Ref(dhcp_options),
                )
            )
        else:
            dhcp_options = t.add_resource(
                ec2.DHCPOptions(
                    'DHCPOptions',
                    DomainNameServers=['AmazonProvidedDNS', ],
                )
            )
            t.add_resource(
                ec2.VPCDHCPOptionsAssociation(
                    'DHCPAssociation',
                    VpcId=VPC_ID,
                    DhcpOptionsId=Ref(dhcp_options),
                )
            )

    def create_gateway(self):
        t = self.template
        t.add_resource(ec2.InternetGateway(GATEWAY))
        t.add_resource(
            ec2.VPCGatewayAttachment(
                GW_ATTACH,
                VpcId=VPC_ID,
                InternetGatewayId=Ref(GATEWAY)
            )
        )

    def create_network(self):
        t = self.template
        variables = self.get_variables()
        self.create_gateway()
        t.add_resource(ec2.NetworkAcl('DefaultACL',
                                      VpcId=VPC_ID))

        self.create_nat_security_groups()
        subnets = {'public': [], 'private': []}
        net_types = subnets.keys()
        zones = []
        for i in range(variables["AZCount"]):
            az = Select(i, GetAZs(""))
            zones.append(az)
            name_suffix = i
            for net_type in net_types:
                name_prefix = net_type.capitalize()
                subnet_name = "%sSubnet%s" % (name_prefix, name_suffix)
                subnets[net_type].append(subnet_name)
                t.add_resource(
                    ec2.Subnet(
                        subnet_name,
                        AvailabilityZone=az,
                        VpcId=VPC_ID,
                        DependsOn=GW_ATTACH,
                        CidrBlock=variables.get("%sSubnets" % name_prefix)[i],
                        Tags=Tags(type=net_type)
                    )
                )

                route_table_name = "%sRouteTable%s" % (name_prefix,
                                                       name_suffix)
                t.add_resource(
                    ec2.RouteTable(
                        route_table_name,
                        VpcId=VPC_ID,
                        Tags=[ec2.Tag('type', net_type)]
                    )
                )
                t.add_resource(
                    ec2.SubnetRouteTableAssociation(
                        "%sRouteTableAssociation%s" % (name_prefix,
                                                       name_suffix),
                        SubnetId=Ref(subnet_name),
                        RouteTableId=Ref(route_table_name)
                    )
                )

                route_name = '%sRoute%s' % (name_prefix, name_suffix)
                if net_type == 'public':
                    # the public subnets are where the NAT instances live,
                    # so their default route needs to go to the AWS
                    # Internet Gateway
                    t.add_resource(
                        ec2.Route(
                            route_name,
                            RouteTableId=Ref(route_table_name),
                            DestinationCidrBlock="0.0.0.0/0",
                            GatewayId=Ref(GATEWAY)
                        )
                    )
                    self.create_nat_instance(i, subnet_name)
                else:
                    # Private subnets are where actual instances will live
                    # so their gateway needs to be through the nat instances
                    if variables["UseNatGateway"]:
                        instance_id = NOVALUE
                        nat_gateway_id = Ref(NAT_GATEWAY_NAME % name_suffix)
                    else:
                        instance_id = Ref(NAT_INSTANCE_NAME % name_suffix)
                        nat_gateway_id = NOVALUE

                    t.add_resource(
                        ec2.Route(
                            route_name,
                            RouteTableId=Ref(route_table_name),
                            DestinationCidrBlock='0.0.0.0/0',
                            InstanceId=instance_id,
                            NatGatewayId=nat_gateway_id,
                        )
                    )

        for net_type in net_types:
            t.add_output(
                Output(
                    "%sSubnets" % net_type.capitalize(),
                    Value=Join(
                        ",",
                        [Ref(sn) for sn in subnets[net_type]]
                    )
                )
            )

            for i, sn in enumerate(subnets[net_type]):
                t.add_output(
                    Output(
                        "%sSubnet%d" % (net_type.capitalize(), i),
                        Value=Ref(sn)
                    )
                )

        self.template.add_output(Output(
            "AvailabilityZones",
            Value=Join(",", zones)))

        for i, az in enumerate(zones):
            t.add_output(
                Output(
                    "AvailabilityZone%d" % (i),
                    Value=az
                )
            )

    def create_nat_security_groups(self):
        t = self.template
        variables = self.get_variables()

        # Only create security group if NAT Instances are being used.
        if not variables["UseNatGateway"]:
            nat_private_in_all_rule = ec2.SecurityGroupRule(
                IpProtocol='-1', FromPort='-1', ToPort='-1',
                SourceSecurityGroupId=Ref(DEFAULT_SG)
            )

            nat_public_out_all_rule = ec2.SecurityGroupRule(
                IpProtocol='-1', FromPort='-1', ToPort='-1', CidrIp='0.0.0.0/0'
            )

            return t.add_resource(
                ec2.SecurityGroup(
                    NAT_SG,
                    VpcId=VPC_ID,
                    GroupDescription='NAT Instance Security Group',
                    SecurityGroupIngress=[nat_private_in_all_rule],
                    SecurityGroupEgress=[nat_public_out_all_rule, ]
                )
            )

    def create_nat_instance(self, zone_id, subnet_name):
        t = self.template
        variables = self.get_variables()
        suffix = zone_id
        eip_name = "NATExternalIp%s" % suffix

        if variables["UseNatGateway"]:
            gateway_name = NAT_GATEWAY_NAME % suffix
            t.add_resource(
                ec2.NatGateway(
                    gateway_name,
                    AllocationId=GetAtt(eip_name, 'AllocationId'),
                    SubnetId=Ref(subnet_name),
                )
            )

            t.add_output(
                Output(
                    gateway_name + "Id",
                    Value=Ref(gateway_name)
                )
            )

            # Using NAT Gateways, leave the EIP unattached - it gets allocated
            # to the NAT Gateway in that resource above
            eip_instance_id = Ref("AWS::NoValue")
        else:
            image_id = FindInMap(
                'AmiMap',
                Ref("AWS::Region"),
                Ref("ImageName")
            )
            instance_name = NAT_INSTANCE_NAME % suffix
            t.add_resource(
                ec2.Instance(
                    instance_name,
                    Condition="UseNatInstances",
                    ImageId=image_id,
                    SecurityGroupIds=[Ref(DEFAULT_SG), Ref(NAT_SG)],
                    SubnetId=Ref(subnet_name),
                    InstanceType=variables["InstanceType"],
                    SourceDestCheck=False,
                    KeyName=variables["SshKeyName"],
                    Tags=[ec2.Tag('Name', 'nat-gw%s' % suffix)],
                    DependsOn=GW_ATTACH
                )
            )
            t.add_output(
                Output(
                    instance_name + "PublicHostname",
                    Value=GetAtt(instance_name, "PublicDnsName")
                )
            )
            t.add_output(
                Output(
                    instance_name + "InstanceId",
                    Value=Ref(instance_name)
                )
            )

            # Since we're using NAT instances, go ahead and attach the EIP
            # to the NAT instance
            eip_instance_id = Ref(instance_name)

        t.add_resource(
            ec2.EIP(
                eip_name,
                Domain='vpc',
                InstanceId=eip_instance_id,
                DependsOn=GW_ATTACH
            )
        )

    def create_template(self):
        self.create_vpc()
        self.create_internal_zone()
        self.create_default_security_group()
        self.create_dhcp_options()
        self.create_network()
