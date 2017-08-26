from troposphere import ec2, efs
from troposphere import Join, Output, Ref

from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import EC2VPCId, TroposphereType


class ElasticFileSystem(Blueprint):
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
        'IPAddresses': {
            'type': str,
            'description': 'List of IP addresses to assign to mount targets. '
                           'Omit to assign automatically. '
                           'Corresponds to Subnets listed in the same order.',
            'default': ''
        },
        'SecurityGroups': {
            'type': TroposphereType(ec2.SecurityGroup, many=True,
                                    validate=False),
            'description': 'Definition of SecurityGroups to be created and '
                           'assigned to the Mount Targets. The VpcId property '
                           'will be filled from the similarly named variable '
                           'of this blueprint, so it can be ommited. '
                           'Omit this parameter entirely, or make it an empty '
                           'list to avoid creating any groups (and use the '
                           'ExtraSecurityGroups variable instead)',
            'default': []
        },
        'ExtraSecurityGroups': {
            'type': str,
            'description': 'Comma-separated list of existing SecurityGroups '
                           'to be assigned to the EFS.',
            'default': ''
        }
    }

    def create_efs_filesystem(self):
        t = self.template
        v = self.get_variables()

        fs = t.add_resource(efs.FileSystem(
            'EfsFileSystem',
            FileSystemTags=efs.Tags(v['FileSystemTags']),
            PerformanceMode=v['PerformanceMode']))

        t.add_output(Output(
            'EfsFileSystemId',
            Value=Ref(fs)))

        return fs

    def create_efs_security_groups(self):
        t = self.template
        v = self.get_variables()

        new_sgs = []
        for sg in v['SecurityGroups']:
            sg.VpcId = Ref('VpcId')
            sg.validate()

            t.add_resource(sg)
            new_sgs.append(Ref(sg))

        t.add_output(Output(
            'EfsSecurityGroupIds',
            Value=Join(',', new_sgs)))

        existing_sgs = v['ExtraSecurityGroups'].split(',')
        return new_sgs + existing_sgs

    def create_efs_mount_targets(self, fs, sgs):
        t = self.template
        v = self.get_variables()

        subnets = v['Subnets'].split(',')
        ips = v['IPAddresses'] and v['IPAddresses'].split(',')
        if ips and len(ips) != len(subnets):
            raise ValueError('Subnets and IPAddresses must have same count')

        mount_targets = []
        for i, subnet in enumerate(subnets):
            mount_target = efs.MountTarget(
                'EfsMountTarget{}'.format(i + 1),
                FileSystemId=Ref(fs),
                SubnetId=subnet,
                SecurityGroups=sgs)

            if ips:
                mount_target.IpAddress = ips[i]

            t.add_resource(mount_target)
            mount_targets.append(mount_target)

        t.add_output(Output(
            'EfsMountTargetIds',
            Value=Join(',', list(map(Ref, mount_targets)))))

    def create_template(self):
        fs = self.create_efs_filesystem()
        sgs = self.create_efs_security_groups()
        self.create_efs_mount_targets(fs, sgs)
