from stacker.context import Context
from stacker.config import Config
from stacker.variables import Variable

from stacker_blueprints.asg import FlexibleAutoScalingGroup
from stacker.blueprints.testutil import BlueprintTestCase


class TestBlueprint(BlueprintTestCase):
    def setUp(self):
        self.launch_config = {
            "ImageId": "i-abc1234",
            "InstanceType": "m3.medium",
            "KeyName": "mock_ssh_key",
            "SecurityGroups": ["sg-abc1234", "sg-bcd2345"],
        }
        self.asg_config = {
            "MinSize": 1,
            "MaxSize": 3,
        }

        self.common_variables = {
            "LaunchConfiguration": {
                "LaunchConfiguration": self.launch_config,
            },
            "AutoScalingGroup": {
                "AutoScalingGroup": self.asg_config
            },
        }
        self.ctx = Context(config=Config({"namespace": "test"}))

    def create_blueprint(self, name):
        return FlexibleAutoScalingGroup(name, self.ctx)

    def generate_variables(self):
        return [Variable(k, v) for k, v in self.common_variables.items()]

    def test_create_template_provided_launch_config_name(self):
        blueprint = self.create_blueprint(
            "test_asg_flexible_autoscaling_group_provided_launch_config"
        )

        self.asg_config["LaunchConfigurationName"] = "launch_config"

        blueprint.resolve_variables(self.generate_variables())
        with self.assertRaises(ValueError):
            blueprint.create_template()

    def test_create_template(self):
        blueprint = self.create_blueprint(
            "test_asg_flexible_autoscaling_group"
        )

        self.asg_config["AvailabilityZones"] = ["us-east-1a", "us-east-1b"]

        blueprint.resolve_variables(self.generate_variables())
        blueprint.create_template()
        self.assertRenderedBlueprint(blueprint)
