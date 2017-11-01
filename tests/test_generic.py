import unittest

from stacker.blueprints.testutil import BlueprintTestCase
from stacker.context import Context
from stacker.config import Config
from stacker.variables import Variable

from stacker_blueprints.generic import GenericResourceCreator


class TestGenericResourceCreator(BlueprintTestCase):
    def setUp(self):
        self.ctx = Context(config=Config({'namespace': 'test'}))

    def test_create_template(self):
        blueprint = GenericResourceCreator(
            'test_generic_GenericResourceCreator', self.ctx
        )
        blueprint.resolve_variables(
            [
                Variable('Class', 'ec2.Volume'),
                Variable('Output', 'VolumeId'),
                Variable('Properties', {
                    'VolumeType': 'gp2',
                    'Size': '600',
                    'Encrypted': 'true',
                    'AvailabilityZone': 'us-east-1b',
                }),
            ]
        )
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)


if __name__ == '__main__':
    unittest.main()
