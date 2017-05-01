import unittest

from stacker.blueprints.testutil import BlueprintTestCase
from stacker.context import Context
from stacker.variables import Variable

from stacker_blueprints.route53 import DNSRecords


class TestRepositories(BlueprintTestCase):
    def setUp(self):
        self.ctx = Context({'namespace': 'test'})

    def test_create_template(self):
        blueprint = DNSRecords('test_route53_dnsrecords', self.ctx)
        blueprint.resolve_variables(
            [
                Variable(
                    "RecordSets",
                    {
                        "TestHost": {
                            "Name": "host.testdomain.com.",
                            "Type": "A",
                            "ResourceRecords": ["10.0.0.1"],
                        },
                        "TestHost2": {
                            "Name": "host2.testdomain.com.",
                            "Type": "A",
                            "ResourceRecords": ["10.0.0.2"],
                        },
                    }
                )
            ]
        )
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)

    def test_specify_multiple_defaults_fail(self):
        blueprint = DNSRecords('test_route53_dnsrecords_multiple_defaults',
                               self.ctx)
        blueprint.resolve_variables(
            [
                Variable(
                    "RecordSets",
                    {
                        "TestHost": {
                            "Name": "host.testdomain.com.",
                            "Type": "A",
                            "ResourceRecords": ["10.0.0.1"],
                        },
                    }
                ),
                Variable("DefaultHostedZoneId", "fake_zone_id"),
                Variable("DefaultHostedZoneName", "fake_zone_name"),
            ]
        )
        with self.assertRaises(ValueError):
            blueprint.create_template()

    def test_valid_default(self):
        blueprint = DNSRecords('test_route53_dnsrecords_defaults', self.ctx)
        blueprint.resolve_variables(
            [
                Variable(
                    "RecordSets",
                    {
                        "TestHost": {
                            "Name": "host.testdomain.com.",
                            "Type": "A",
                            "ResourceRecords": ["10.0.0.1"],
                        },
                        "TestHost2": {
                            "Name": "host2.testdomain.com.",
                            "Type": "A",
                            "ResourceRecords": ["10.0.0.2"],
                            "HostedZoneId": "set_zone_id",
                        },
                    }
                ),
                Variable("DefaultHostedZoneId", "fake_zone_id"),
            ]
        )
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)


if __name__ == '__main__':
    unittest.main()
