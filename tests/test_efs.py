import unittest

from stacker.blueprints.testutil import BlueprintTestCase
from stacker.context import Context
from stacker.variables import Variable

from stacker_blueprints.efs import ElasticFileSystem


class TestElasticFileSystem(BlueprintTestCase):
    def setUp(self):
        self.ctx = Context({'namespace': 'test'})

    def test_create_template(self):
        blueprint = ElasticFileSystem('test_efs_ElasticFileSystem', self.ctx)
        variables = {
            'VpcId': 'vpc-11111111',
            'PerformanceMode': 'generalPurpose',
            'FileSystemTags': {
                'Hello': 'World'
            },
            'Subnets': 'subnet-11111111,subnet-22222222',
            'IPAddresses': '172.16.1.10,172.16.2.10',
            'SecurityGroups': {
                'EfsSg1': {
                    'GroupDescription': 'EFS SG 1',
                    'SecurityGroupIngress': [
                        {'IpProtocol': 'tcp', 'FromPort': 2049, 'ToPort': 2049,
                         'CidrIp': '172.16.0.0/12'}
                    ]
                },
                'EfsSg2': {
                    'GroupDescription': 'EFS SG 2',
                    'SecurityGroupIngress': [
                        {'IpProtocol': 'tcp', 'FromPort': 2049, 'ToPort': 2049,
                         'SourceSecurityGroupId': 'sg-11111111'}
                    ]
                }
            },
            'ExtraSecurityGroups': 'sg-22222222,sg-33333333'
        }
        blueprint.resolve_variables(
            [Variable(k, v) for k, v in variables.items()])
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)


if __name__ == '__main__':
    unittest.main()
