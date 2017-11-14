from stacker.blueprints.base import Blueprint

from troposphere import (
    sns,
    sqs,
    Ref,
    GetAtt,
    Output,
)

from . import util

import awacs
import awacs.sqs

from awacs.aws import (
    Policy,
    Statement,
    Condition,
    ArnEquals,
    Principal,
)


def queue_policy(sns_arn, sqs_arns):
    stmts = []
    for arn in sqs_arns:
        stmts.append(
            Statement(
                Effect="Allow",
                Principal=Principal("*"),
                Action=[awacs.sqs.SendMessage],
                Resource=[arn],
                Condition=Condition(
                    ArnEquals({"aws:SourceArn": sns_arn})
                )
            )
        )

    return Policy(Statement=stmts)


def validate_topic(topic):
    sns_topic_properties = [
        "DisplayName",
        "Subscription",
    ]

    util.check_properties(topic, sns_topic_properties, "SNS")

    return topic


def validate_topics(topics):
    validated_topics = {}
    for topic_name, topic_config in topics.iteritems():
        validated_topics[topic_name] = validate_topic(topic_config)

    return validated_topics


class Topics(Blueprint):
    """
    Manages the creation of SNS topics.
    """

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

    def create_sqs_policy(self, topic_name, topic_arn, topic_subs):
        """
        This method creates the SQS policy needed for an SNS subscription. It
        also takes the ARN of the SQS queue and converts it to the URL needed
        for the subscription, as that takes a URL rather than the ARN.
        """
        t = self.template

        arn_endpoints = []
        url_endpoints = []
        for sub in topic_subs:
            arn_endpoints.append(sub["Endpoint"])
            split_endpoint = sub["Endpoint"].split(":")
            queue_url = "https://%s.%s.amazonaws.com/%s/%s" % (
                split_endpoint[2],  # literally "sqs"
                split_endpoint[3],  # AWS region
                split_endpoint[4],  # AWS ID
                split_endpoint[5],  # Queue name
            )
            url_endpoints.append(queue_url)

        policy_doc = queue_policy(topic_arn, arn_endpoints)

        t.add_resource(
            sqs.QueuePolicy(
                topic_name + "SubPolicy",
                PolicyDocument=policy_doc,
                Queues=url_endpoints,
            )
        )

    def create_topic(self, topic_name, topic_config):
        """
        Creates the SNS topic, along with any subscriptions requested.
        """
        topic_subs = []
        t = self.template

        if "Subscription" in topic_config:
            topic_subs = topic_config["Subscription"]

        t.add_resource(
            sns.Topic.from_dict(
                topic_name,
                topic_config
            )
        )

        topic_arn = Ref(topic_name)

        t.add_output(
            Output(topic_name + "Name", Value=GetAtt(topic_name, "TopicName"))
        )
        t.add_output(Output(topic_name + "Arn", Value=topic_arn))

        sqs_subs = [sub for sub in topic_subs if sub["Protocol"] == "sqs"]
        if sqs_subs:
            self.create_sqs_policy(topic_name, topic_arn, sqs_subs)
