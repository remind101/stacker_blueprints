from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import TroposphereType

from troposphere import logs, Output, Ref


class SubscriptionFilters(Blueprint):

    VARIABLES = {
        "SubscriptionFilters": {
            "type": TroposphereType(logs.SubscriptionFilter, many=True),
            "description": "Subscription filters to create.",
        }
    }

    def create_template(self):
        t = self.template
        variables = self.get_variables()

        for _filter in variables["SubscriptionFilters"]:
            t.add_resource(_filter)
            t.add_output(
                Output(
                    "%sName" % _filter.title,
                    Value=Ref(_filter)
                )
            )
