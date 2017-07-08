from troposphere import (
    Ref, Output
)

from stacker.blueprints.base import Blueprint
from stacker.util import load_object_from_string


class GenericResourceCreator(Blueprint):
    """ Generic Blueprint for creating a resource """
    def add_cfn_description(self):
        """ Boilerplate for CFN Template """
        template = self.template
        template.add_version('2010-09-09')
        template.add_description('Generic Resource Creator - 1.0.0')

    """

    *** NOTE ***    Template Version Reminder

    Make Sure you bump up the template version number above if submitting
    updates to the repo. This is the only way we can tell which version of
    a template is in place on a running resouce.


    Example yaml:

    - name: generic-resource-volume
        class_path: blueprints.generic.GenericResourceCreator
        variables:
            Class: ec2.Volume
            Output: VolumeId
            Properties:
                VolumeType: gp2
                Size: 5
                Encrypted: true
                AvailabilityZone: us-east-1b

    """

    VARIABLES = {
        'Class':
            {'type': str,
             'description': 'The troposphere class to create, '
                            'e.g.: ec2.Volume'},
        'Output':
            {'type': str,
             'description': 'The output field that should be created, '
                            'e.g.: VolumeId'},
        'Properties':
            {'type': dict,
             'description': 'The list of properties to use for the '
                            'Troposphere class'},
    }

    def setup_resource(self):
        """ Setting Up Resource """
        template = self.template
        variables = self.get_variables()

        tclass = variables['Class']
        tprops = variables['Properties']
        output = variables['Output']

        klass = load_object_from_string('troposphere.' + tclass)

        # Warning - sometimes, Troposhpere expects a datatype
        # that is strange, for example ec2.Volume.Size expects
        # to be a string.  In those cases, you should make a PR
        # with Troposhpere to fix it, but as a workaround you
        # can quote the value in the yaml to force detection
        # as a string

        instance = klass.from_dict('ResourceRefName', tprops)

        template.add_resource(instance)
        template.add_output(Output(
            output,
            Description="A reference to the object created in this blueprint",
            Value=Ref(instance)
        ))

    def create_template(self):
        """ Create the CFN template """
        self.add_cfn_description()
        self.setup_resource()
