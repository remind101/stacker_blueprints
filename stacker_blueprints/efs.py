from troposphere import ec2, efs
from troposphere import Join, Output, Ref, Split

from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import EC2VPCId, EC2SecurityGroupIdList


class EFSBlueprint(Blueprint):
    VARIABLES = {
        'VpcId': {
            'type': EC2VPCId,
            'description': 'VPC ID to create resources'
        },
        'PerformanceMode': {
            'type': str,
            'description': 'The performance mode of the file system',
            'default': 'generalPurpose'
        },
        'FileSystemTags': {
            'type': dict,
            'description': 'Tags to associate with the file system.',
            'default': {}
        },
        'Subnets': {
            'type': str,
            'description': 'Comma-delimited list of subnets to deploy private '
                           'mount targets in.'
        },
        'SecurityGroups': {
            'type': str,
            'description': 'Security groups to place mount targets in. '
                           'Omit to create automatically from '
                           'AllowedCIDRs',
            'default': ''
        },
        'IPAddresses': {
            'type': str,
            'description': 'List of IP addresses to assign to mount targets. '
                           'Omit to assign automatically. '
                           'Corresponds to Subnets listed in the same order.',
            'default': ''
        },
        'AllowedCIDRs': {
            'type': list,
            'description': 'List of CIDRs to allow access to the filesystem'
                           'Leave empty to avoid creating default security '
                           'group.',
            'default': []
        }
    }

    def create_efs_security_group(self):
        t = self.template
        v = self.get_variables()

        cidrs = v['AllowedCIDRs']
        if not cidrs:
            self.efs_sg = None
            return

        self.efs_sg = t.add_resource(ec2.SecurityGroup(
            'EFSSecurityGroup',
            GroupDescription='{} EFS Access'.format(self.name),
            VpcId=Ref('VpcId')))

        for i, cidr in enumerate(cidrs):
            t.add_resource(ec2.SecurityGroupIngress(
                'EFSSecurityGroupIngress{}'.format(i + 1),
                IpProtocol='tcp',
                FromPort='2049',
                ToPort='2049',
                CidrIp=cidr,
                GroupId=Ref(self.efs_sg)))

    def create_efs_mount_targets(self, fs):
        t = self.template
        v = self.get_variables()

        subnets = v['Subnets'].split(',')
        ips = v['IPAddresses'] and v['IPAddresses'].split(',')
        if ips and len(ips) != len(subnets):
            raise ValueError('Subnets and IPAddresses must have same count')

        mount_targets = []

        if self.efs_sg and v['SecurityGroups']:
            sgs = Join(',', [Ref(self.efs_sg), v['SecurityGroups']])
        elif self.efs_sg:
            sgs = Ref(self.efs_sg)
        else:
            sgs = v['SecurityGroups']

        for i, subnet in enumerate(subnets):
            params = {'IpAddress': ips[i]} if ips else {}

            mount_target = t.add_resource(efs.MountTarget(
                'EFSMountTarget{}'.format(i + 1),
                FileSystemId=Ref(fs),
                SubnetId=subnet,
                SecurityGroups=Split(',', sgs),
                **params))

            mount_targets.append(mount_target)

        t.add_output(Output(
            'MountTargetIds',
            Value=Join(',', list(map(Ref, mount_targets)))))

    def create_template(self):
        t = self.template
        v = self.get_variables()

        fs = t.add_resource(efs.FileSystem(
            'EFSFileSystem',
            FileSystemTags=efs.Tags(v['FileSystemTags']),
            PerformanceMode=v['PerformanceMode']))

        t.add_output(Output(
            'FileSystemId',
            Value=Ref(fs)))

        self.create_efs_security_group()
        self.create_efs_mount_targets(fs)
