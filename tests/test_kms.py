from stacker.context import Context
from stacker.config import Config
from stacker.variables import Variable

from stacker_blueprints.kms import Key

from stacker.blueprints.testutil import BlueprintTestCase


class TestKmsKey(BlueprintTestCase):
    def setUp(self):
        self.ctx = Context(config=Config({'namespace': 'test'}))

    def test_kms_key(self):
        blueprint = Key('kms_key_a', self.ctx)
        blueprint.resolve_variables(
            [
                Variable("KeyAlias", "alias/a-test-key"),
                Variable("Properties", {"Description": "a KMS test-key."}),
            ]
        )
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_kms_key_alias_not_in_keyalias(self):
        blueprint = Key('kms_key_b', self.ctx)
        blueprint.resolve_variables(
            [
                Variable("KeyAlias", "b-test-key"),
                Variable("Properties", {"Description": "b KMS test-key."}),
            ]
        )
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_kms_key_without_properties(self):
        blueprint = Key('kms_key_c', self.ctx)
        blueprint.resolve_variables(
            [
                Variable("KeyAlias", "alias/c-test-key"),
            ]
        )
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_kms_key_attributes_is_deprecated(self):
        blueprint = Key('kms_key_attributes_deprecated', self.ctx)
        blueprint.resolve_variables(
            [
                Variable("KeyAlias", "c-test-key"),
                Variable("Attributes", {"Description": "c KMS test-key."}),
            ]
        )
        with self.assertRaises(DeprecationWarning):
            blueprint.create_template()
