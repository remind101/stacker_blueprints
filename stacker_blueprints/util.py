from collections import Mapping

from troposphere import Tags


def check_properties(properties, allowed_properties, resource):
    """Checks the list of properties in the properties variable against the
    property list provided by the allowed_properties variable. If any property
    does not match the properties in allowed_properties, a ValueError is
    raised to prevent unexpected behavior when creating resources.

    properties: The config (as dict) provided by the configuration file
    allowed_properties: A list of strings representing the available params
        for a resource.
    resource: A string naming the resource in question for the error
        message.
    """
    for key in properties.keys():
        if key not in allowed_properties:
            raise ValueError(
                "%s is not a valid property of %s" % (key, resource)
            )


def _tags_to_dict(tag_list):
    return dict((tag['Key'], tag['Value']) for tag in tag_list)


def merge_tags(left, right, factory=Tags):
    """
    Merge two sets of tags into a new troposphere object

    Args:
        left (Union[dict, troposphere.Tags]): dictionary or Tags object to be
            merged with lower priority
        right (Union[dict, troposphere.Tags]): dictionary or Tags object to be
            merged with higher priority
        factory (type): Type of object to create. Defaults to the troposphere
            Tags class.
    """

    if isinstance(left, Mapping):
        tags = dict(left)
    elif hasattr(left, 'tags'):
        tags = _tags_to_dict(left.tags)
    else:
        tags = _tags_to_dict(left)

    if isinstance(right, Mapping):
        tags.update(right)
    elif hasattr(left, 'tags'):
        tags.update(_tags_to_dict(right.tags))
    else:
        tags.update(_tags_to_dict(right))

    return factory(**tags)
