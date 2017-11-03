import unittest
from stacker.context import Context, Config
from stacker.variables import Variable
from stacker_blueprints.s3 import Buckets
from stacker.blueprints.testutil import BlueprintTestCase


class TestBlueprint(BlueprintTestCase):
    def setUp(self):
        self.variables = [
            Variable('Buckets', {
                'Simple': {},
                'Cycle': {
                    'LifecycleConfiguration': {
                        'Rules': [{
                            'Status': 'Enabled',
                            'ExpirationInDays': 40,
                        }],
                    },
                }
            }),
            Variable('ReadRoles', [
                'Role1',
                'Role2',
            ]),
            Variable('ReadWriteRoles', [
                'Role3',
                'Role4',
            ]),
        ]

    def test_s3(self):
        ctx = Context(config=Config({'namespace': 'test'}))
        blueprint = Buckets('buckets', ctx)
        blueprint.resolve_variables(self.variables)
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)
