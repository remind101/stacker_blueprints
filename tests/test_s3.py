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

    def test_s3_static_website(self):
        """Test a static website blog bucket."""
        ctx = Context(config=Config({'namespace': 'test'}))
        blueprint = Buckets('s3_static_website', ctx)

        v = self.variables = [
            Variable('Buckets', {
                'Blog': {
                    'AccessControl': 'PublicRead',
                    'WebsiteConfiguration' : {
                        'IndexDocument': 'index.html'
                    }
                },
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

        blueprint.resolve_variables(v)
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)
