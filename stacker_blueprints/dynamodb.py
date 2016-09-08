from stacker.blueprints.base import Blueprint
from . import util

from troposphere import (
    dynamodb2,
    Ref,
    GetAtt,
    Output,
)

from troposphere.route53 import RecordSetType

def prep_schemata(config):
    try:
        schemata = []
        for schema in config["KeySchema"]:
            schemata.append(dynamodb2.KeySchema(**schema))

    except IndexError:
        raise IndexError(
            "The key schema is required for the creation of a DynamoDB table."
        )

    return schemata

def prep_projection(config):
    return dynamodb2.Projection(**config["Projection"])

def prep_throughput(config):
    try:
        return dynamodb2.ProvisionedThroughput(
            **config["ProvisionedThroughput"]
        )
    except IndexError:
        raise IndexError(
            "ProvisionedThroughput values are required for the creation of " +
            "a DynamoDB table or index."
        )

def prep_config(raw_config):
    prepped_config = {}

    dynamodb_table_properties = [
        "AttributeDefinitions",
        "GlobalSecondaryIndexes",
        "KeySchema",
        "LocalSecondaryIndexes",
        "ProvisionedThroughput",
        "StreamSpecification",
    ]

    util.check_properties(
        raw_config,
        dynamodb_table_properties,
        "DynamoDB",
    )

    # AttributeDefinitions are required, so raise an IndexError if this
    # doesn't work.
    try:
        attributes = []
        for attribute in raw_config["AttributeDefinitions"]:
            attributes.append(dynamodb2.AttributeDefinition(**attribute))

        prepped_config["AttributeDefinitions"] = attributes
    except IndexError:
        raise IndexError(
            "Attribute definitions are required for the creation of a " +
            "DynamoDB table."
        )

    # Global Secondary Index section.
    if "GlobalSecondaryIndexes" in raw_config:
        # AWS limits us to 5 GSIs.  Check for that and bail if there's more.
        if len(raw_config["GlobalSecondaryIndexes"]) > 5:
            raise ValueError(
                "A DynamoDB table can only have a maximum of 5 GSIs."
            )

        gsis = []
        for gsi in raw_config["GlobalSecondaryIndexes"]:
            gsi["KeySchema"] = prep_schemata(gsi)
            gsi["Projection"] = prep_projection(gsi)
            gsi["ProvisionedThroughput"] = prep_throughput(gsi)
            gsis.append(dynamodb2.GlobalSecondaryIndex(**gsi))

        prepped_config["GlobalSecondaryIndexes"] = gsis

    # KeySchema section
    prepped_config["KeySchema"] = prep_schemata(raw_config)

    # LocalSecondaryIndexes section
    if "LocalSecondaryIndexes" in raw_config:
        # Another limit of 5.  Check and bail if more than that.
        if len(raw_config["LocalSecondaryIndexes"]) > 5:
            raise ValueError(
                "A DynamoDB table can only have a maximum of 5 LSIs."
            )

        lsis = []
        for lsi in raw_config["LocalSecondaryIndexes"]:
            lsi["KeySchema"] = prep_schemata(lsi)
            lsi["Projection"] = prep_projection(lsi)
            lsi["ProvisionedThroughput"] = prep_throughput(lsi)
            lsis.append(dynamodb2.LocalSecondaryIndex(**lsi))

        prepped_config["LocalSecondaryIndexes"] = lsis

    # ProvisionedThroughput section.
    prepped_config["ProvisionedThroughput"] = prep_throughput(raw_config)

    # StreamSpecification section
    stream_enabled = False
    if "StreamSpecification" in raw_config:
        stream_enabled = True
        prepped_config["StreamSpecification"] = dynamodb2.StreamSpecification(
            **raw_config["StreamSpecification"]
        )

    return prepped_config, stream_enabled

class DynamoDB(Blueprint):
    """Manages the creation of DynamoDB tables."""

    VARIABLES = {
        "Tables": {
            "type": dict,
            "description": "Dictionary of DynamoDB table definitions",
        }
    }

    def create_template(self):
        variables = self.get_variables()

        for table_name, table_config in variables["Tables"].iteritems():
            table_config, stream_enabled = prep_config(table_config)
            self.create_table(table_name, table_config, stream_enabled)

    def create_table(self, table_name, table_config, stream_enabled):
        t = self.template

        t.add_resource(
            dynamodb2.Table(
                table_name,
                **table_config
            )
        )

        if stream_enabled:
            t.add_output(Output(table_name + "StreamArn", Value=GetAtt(table_name, "StreamArn")))
        
        t.add_output(Output(table_name + "Name", Value=Ref(table_name)))
