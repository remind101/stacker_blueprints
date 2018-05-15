from stacker.context import Context
from stacker.config import Config
from stacker.variables import Variable
from stacker_blueprints.vpc import VPC2
from stacker.blueprints.testutil import BlueprintTestCase

from troposphere.route53 import HostedZone

VPC_NAME = "MyVPC"


class TestVPC2(BlueprintTestCase):
    def setUp(self):
        self.ctx = Context(config=Config({'namespace': 'test'}))
        self.common_variables = {
            "VPC": {
                VPC_NAME: {
                    "CidrBlock": "10.0.0.0/16"
                }
            }
        }

    def create_blueprint(self, name):
        return VPC2(name, self.ctx)

    def generate_variables(self, variable_dict=None):
        variable_dict = variable_dict or {}
        self.common_variables.update(variable_dict)

        return [Variable(k, v) for k, v in self.common_variables.items()]

    def test_vpc2_without_internal_zone(self):
        bp = self.create_blueprint("test_vpc2_without_internal_zone")

        bp.resolve_variables(self.generate_variables())
        bp.create_template()
        self.assertRenderedBlueprint(bp)
        self.assertIn(VPC_NAME, bp.template.resources)
        for r in bp.template.resources.values():
            self.assertNotIsInstance(r, HostedZone)

    def test_vpc2_with_internal_zone(self):
        bp = self.create_blueprint("test_vpc2_with_internal_zone")

        variables = {
            "InternalZone": {
                "MyInternalZone": {
                    "Name": "internal."
                }
            }
        }

        bp.resolve_variables(self.generate_variables(variables))
        bp.create_template()
        self.assertRenderedBlueprint(bp)
        self.assertIn(VPC_NAME, bp.template.resources)
        zone = bp.template.resources["MyInternalZone"]
        self.assertEquals(zone.VPCs[0].VPCId.data["Ref"], VPC_NAME)
        dhcp = bp.template.resources["DHCPOptions"]
        self.assertEquals(dhcp.DomainName, "internal.")
