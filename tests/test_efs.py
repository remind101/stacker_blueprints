import unittest

from stacker.blueprints.testutil import BlueprintTestCase
from stacker.context import Context
from stacker.exceptions import ValidatorError
from stacker.variables import Variable

from stacker_blueprints.efs import ElasticFileSystem


EFS_VARIABLES = {
    'VpcId': 'vpc-11111111',
    'PerformanceMode': 'generalPurpose',
    'Tags': {
        'Hello': 'World'
    },
    'Subnets': ['subnet-11111111', 'subnet-22222222'],
    'IpAddresses': ['172.16.1.10', '172.16.2.10'],
    'SecurityGroups': {
        'EfsSg1': {
            'GroupDescription': 'EFS SG 1',
            'SecurityGroupIngress': [
                {'IpProtocol': 'tcp', 'FromPort': 2049, 'ToPort': 2049,
                 'CidrIp': '172.16.0.0/12'}
            ],
            'Tags': [{'Key': 'Foo', 'Value': 'Bar'}]
        },
        'EfsSg2': {
            'GroupDescription': 'EFS SG 2',
            'SecurityGroupIngress': [
                {'IpProtocol': 'tcp', 'FromPort': 2049, 'ToPort': 2049,
                 'SourceSecurityGroupId': 'sg-11111111'}
            ]
        }
    },
    'ExtraSecurityGroups': ['sg-22222222', 'sg-33333333']
}


class TestElasticFileSystem(BlueprintTestCase):
    def setUp(self):
        self.ctx = Context({'namespace': 'test'})

    def test_create_template(self):
        blueprint = ElasticFileSystem('test_efs_ElasticFileSystem', self.ctx)
        variables = EFS_VARIABLES
        blueprint.resolve_variables(
            [Variable(k, v) for k, v in variables.items()])
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_validate_security_group_count_empty(self):
        blueprint = ElasticFileSystem('test_efs_ElasticFileSystem', self.ctx)
        variables = EFS_VARIABLES.copy()
        variables['SecurityGroups'] = {}
        variables['ExtraSecurityGroups'] = []

        with self.assertRaises(ValidatorError):
            blueprint.resolve_variables(
                [Variable(k, v) for k, v in variables.items()])

    def test_validate_security_group_count_exceeded(self):
        blueprint = ElasticFileSystem('test_efs_ElasticFileSystem', self.ctx)
        variables = EFS_VARIABLES.copy()
        variables['ExtraSecurityGroups'] = ['sg-22222222'] * 4

        with self.assertRaises(ValidatorError):
            blueprint.resolve_variables(
                [Variable(k, v) for k, v in variables.items()])

    def test_validate_subnets_empty(self):
        blueprint = ElasticFileSystem('test_efs_ElasticFileSystem', self.ctx)
        variables = EFS_VARIABLES.copy()
        variables['Subnets'] = []

        with self.assertRaises(ValidatorError):
            blueprint.resolve_variables(
                [Variable(k, v) for k, v in variables.items()])

    def test_validate_subnets_ip_addresses_unmatching(self):
        blueprint = ElasticFileSystem('test_efs_ElasticFileSystem', self.ctx)
        variables = EFS_VARIABLES.copy()
        variables['IpAddresses'] = ['172.16.1.10']

        with self.assertRaises(ValidatorError):
            blueprint.resolve_variables(
                [Variable(k, v) for k, v in variables.items()])


if __name__ == '__main__':
    unittest.main()
