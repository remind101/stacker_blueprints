from stacker.blueprints.base import Blueprint

from troposphere import (
    dynamodb2,
    Ref,
    GetAtt,
    Output,
)

from . import util

MAX_GSI_VALUE = 5
MAX_LSI_VALUE = 5


def prep_schemata(config):
    schemata = []
    try:
        schemas = config["KeySchema"]
    except KeyError:
        raise KeyError(
            "The key schema is required for the creation of a DynamoDB table."
        )

    for schema in schemas:
        schemata.append(dynamodb2.KeySchema(**schema))

    return schemata


def prep_projection(config):
    return dynamodb2.Projection(**config["Projection"])


def prep_throughput(config):
    try:
        return dynamodb2.ProvisionedThroughput(
            **config["ProvisionedThroughput"]
        )
    except KeyError:
        raise KeyError(
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

    # AttributeDefinitions are required, so raise a KeyError if this doesn't
    # work.
    try:
        config_attributes = raw_config["AttributeDefinitions"]
    except KeyError:
        raise KeyError(
            "Attribute definitions are required for the creation of a " +
            "DynamoDB table."
        )

    attributes = []
    for attribute in config_attributes:
        attributes.append(dynamodb2.AttributeDefinition(**attribute))

    prepped_config["AttributeDefinitions"] = attributes

    if "GlobalSecondaryIndexes" in raw_config:
        # AWS limits us to 5 GSIs.  Check for that and bail if there's more.
        if len(raw_config["GlobalSecondaryIndexes"]) > MAX_GSI_VALUE:
            raise ValueError(
                "A DynamoDB table can only have a maximum of 5 global " +
                "secondary indexes."
            )

        gsis = []
        for gsi in raw_config["GlobalSecondaryIndexes"]:
            gsi["KeySchema"] = prep_schemata(gsi)
            gsi["Projection"] = prep_projection(gsi)
            gsi["ProvisionedThroughput"] = prep_throughput(gsi)
            gsis.append(dynamodb2.GlobalSecondaryIndex(**gsi))

        prepped_config["GlobalSecondaryIndexes"] = gsis

    prepped_config["KeySchema"] = prep_schemata(raw_config)

    if "LocalSecondaryIndexes" in raw_config:
        # Another limit of 5.  Check and bail if more than that.
        if len(raw_config["LocalSecondaryIndexes"]) > MAX_LSI_VALUE:
            raise ValueError(
                "A DynamoDB table can only have a maximum of 5 local " +
                "secondary indexes."
            )

        lsis = []
        for lsi in raw_config["LocalSecondaryIndexes"]:
            lsi["KeySchema"] = prep_schemata(lsi)
            lsi["Projection"] = prep_projection(lsi)
            lsi["ProvisionedThroughput"] = prep_throughput(lsi)
            lsis.append(dynamodb2.LocalSecondaryIndex(**lsi))

        prepped_config["LocalSecondaryIndexes"] = lsis

    prepped_config["ProvisionedThroughput"] = prep_throughput(raw_config)

    if "StreamSpecification" in raw_config:
        prepped_config["StreamSpecification"] = dynamodb2.StreamSpecification(
            **raw_config["StreamSpecification"]
        )

    return prepped_config


def validate_tables(tables):
    prepped_configs = {}
    for table_name, table_config in tables.iteritems():
        prepped_config = prep_config(table_config)
        prepped_configs[table_name] = prepped_config

    return prepped_configs


class DynamoDB(Blueprint):
    """Manages the creation of DynamoDB tables."""

    VARIABLES = {
        "Tables": {
            "type": dict,
            "description": "Dictionary of DynamoDB table definitions",
            "validator": validate_tables,
        }
    }

    def create_template(self):
        variables = self.get_variables()

        for table_name, table_config in variables["Tables"].iteritems():
            stream_enabled = "StreamSpecification" in table_config
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
            t.add_output(
                Output(table_name + "StreamArn",
                       Value=GetAtt(table_name, "StreamArn")))

        t.add_output(Output(table_name + "Name", Value=Ref(table_name)))
