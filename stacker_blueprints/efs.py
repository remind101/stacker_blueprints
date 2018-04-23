from troposphere import ec2, efs
from troposphere import Join, Output, Ref, Tags

from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import TroposphereType
from stacker.exceptions import ValidatorError

from stacker_blueprints.util import merge_tags


class ElasticFileSystem(Blueprint):
    VARIABLES = {
        'VpcId': {
            'type': str,
            'description': 'VPC ID to create resources'
        },
        'PerformanceMode': {
            'type': str,
            'description': 'The performance mode of the file system',
            'default': 'generalPurpose'
        },
        'Tags': {
            'type': dict,
            'description': 'Tags to associate with the created resources',
            'default': {}
        },
        'Subnets': {
            'type': list,
            'description': 'List of subnets to deploy private mount targets in'
        },
        'IpAddresses': {
            'type': list,
            'description': 'List of IP addresses to assign to mount targets. '
                           'Omit or make empty to assign automatically. '
                           'Corresponds to Subnets listed in the same order.',
            'default': []
        },
        'SecurityGroups': {
            'type': TroposphereType(ec2.SecurityGroup, many=True,
                                    optional=True, validate=False),
            'description': "Dictionary of titles to SecurityGroups "
                           "definitions to be created and assigned to this "
                           "filesystem's MountTargets. "
                           "The VpcId property will be filled automatically, "
                           "so it should not be included. \n"
                           "The IDs of the created groups will be exported as "
                           "a comma-separated list in the "
                           "EfsNewSecurityGroupIds output.\n"
                           "Omit this parameter or set it to an empty "
                           "dictionary to not create any groups. In that "
                           "case the ExistingSecurityGroups variable must not "
                           "be empty",
            'default': {}
        },
        'ExtraSecurityGroups': {
            'type': list,
            'description': "List of existing SecurityGroup IDs to be asigned "
                           "to this filesystem's MountTargets",
            'default': []
        }
    }

    def validate_efs_security_groups(self):
        validator = '{}.{}'.format(type(self).__name__,
                                   'validate_efs_security_groups')
        v = self.get_variables()
        count = len(v['SecurityGroups'] or []) + len(v['ExtraSecurityGroups'])

        if count == 0:
            raise ValidatorError(
                'SecurityGroups,ExtraSecurityGroups', validator, count,
                'At least one SecurityGroup must be provided')
        elif count > 5:
            raise ValidatorError(
                'SecurityGroups,ExtraSecurityGroups', validator, count,
                'At most five total SecurityGroups must be provided')

    def validate_efs_subnets(self):
        validator = '{}.{}'.format(type(self).__name__, 'validate_efs_subnets')
        v = self.get_variables()

        subnet_count = len(v['Subnets'])
        if not subnet_count:
            raise ValidatorError(
                'Subnets', validator, v['Subnets'],
                'At least one Subnet must be provided')

        ip_count = len(v['IpAddresses'])
        if ip_count and ip_count != subnet_count:
            raise ValidatorError(
                'IpAddresses', validator, v['IpAddresses'],
                'The number of IpAddresses must match the number of Subnets')

    def resolve_variables(self, provided_variables):
        super(ElasticFileSystem, self).resolve_variables(provided_variables)

        self.validate_efs_security_groups()
        self.validate_efs_subnets()

    def prepare_efs_security_groups(self):
        t = self.template
        v = self.get_variables()

        created_groups = []
        for sg in v['SecurityGroups']:
            sg.VpcId = v['VpcId']
            sg.Tags = merge_tags(v['Tags'], getattr(sg, 'Tags', {}))

            sg = t.add_resource(sg)
            created_groups.append(sg)

        created_group_ids = list(map(Ref, created_groups))
        t.add_output(Output(
            'EfsNewSecurityGroupIds',
            Value=Join(',', created_group_ids)))

        groups_ids = created_group_ids + v['ExtraSecurityGroups']
        return groups_ids

    def create_efs_filesystem(self):
        t = self.template
        v = self.get_variables()

        fs = t.add_resource(efs.FileSystem(
            'EfsFileSystem',
            FileSystemTags=Tags(v['Tags']),
            PerformanceMode=v['PerformanceMode']))

        t.add_output(Output(
            'EfsFileSystemId',
            Value=Ref(fs)))

        return fs

    def create_efs_mount_targets(self, fs):
        t = self.template
        v = self.get_variables()

        groups = self.prepare_efs_security_groups()
        subnets = v['Subnets']
        ips = v['IpAddresses']

        mount_targets = []
        for i, subnet in enumerate(subnets):
            mount_target = efs.MountTarget(
                'EfsMountTarget{}'.format(i + 1),
                FileSystemId=Ref(fs),
                SubnetId=subnet,
                SecurityGroups=groups)

            if ips:
                mount_target.IpAddress = ips[i]

            mount_target = t.add_resource(mount_target)
            mount_targets.append(mount_target)

        t.add_output(Output(
            'EfsMountTargetIds',
            Value=Join(',', list(map(Ref, mount_targets)))))

    def create_template(self):
        fs = self.create_efs_filesystem()
        self.create_efs_mount_targets(fs)
