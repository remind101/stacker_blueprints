from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import TroposphereType

from troposphere import logs, Output, Ref


LOG_RETENTION_VALUES = [
    0, 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827,
    3653
]
LOG_RETENTION_STRINGS = [str(x) for x in LOG_RETENTION_VALUES]


def validate_cloudwatch_log_retention(value):
    if value not in LOG_RETENTION_VALUES:
        raise ValueError(
            "%d is not a valid retention period. Must be one of: %s" % (
                value,
                ', '.join(LOG_RETENTION_STRINGS)
            )
        )
    return value


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
