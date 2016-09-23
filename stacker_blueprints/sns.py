from stacker.blueprints.base import Blueprint

from troposphere import (
    sns,
    Ref,
    GetAtt,
    Output,
)

from . import util


def validate_topic(topic):
    sns_topic_properties = [
        "DisplayName",
        "Subscription",
    ]

    util.check_properties(topic, sns_topic_properties, "SNS")

    if "Subscription" in topic:
        subs = []
        for sub in topic["Subscription"]:
            subs.append(sns.Subscription(**sub))

        topic["Subscription"] = subs

    return topic


def validate_topics(topics):
    validated_topics = {}
    for topic_name, topic_config in topics.iteritems():
        validated_topics[topic_name] = validate_topic(topic_config)

    return validated_topics


class Topics(Blueprint):
    """Manages the creation of SNS topics."""

    VARIABLES = {
        "Topics": {
            "type": dict,
            "description": "Dictionary of SNS Topic definitions",
            "validator": validate_topics,
        }
    }

    def create_template(self):
        variables = self.get_variables()

        for topic_name, topic_config in variables["Topics"].iteritems():
            self.create_topic(topic_name, topic_config)

    def create_topic(self, topic_name, topic_config):
        t = self.template

        t.add_resource(
            sns.Topic(
                topic_name,
                **topic_config
            )
        )

        t.add_output(Output(topic_name + "Name", Value=GetAtt(topic_name, "TopicName")))
        t.add_output(Output(topic_name + "Arn", Value=Ref(topic_name)))
