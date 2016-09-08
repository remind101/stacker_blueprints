def check_properties(properties, property_list, resource):
    """Checks the list of properties in the properties variable against
    the property list provided by the property_list variable. If any
    property does not match the properties in property_list, a ValueError
    is raised to prevent unexpected behavior when creating resources.

    properties: The config (as dict) provided by the configuration file
    property_list: A list of strings representing the available params for
        a resource.
    resource: A string naming the resource in question for the error
        message.
    """
    for key in properties.keys():
        if key not in property_list:
            raise ValueError(
                "%s is not a valid property of %s" % (key, resource)
            )
