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
