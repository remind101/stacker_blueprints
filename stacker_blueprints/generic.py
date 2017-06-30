""" Load dependencies """
from troposphere import (
    Ref, Output
)

from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import (
    CFNString,
    CFNCommaDelimitedList,
)

class generic_resource_creator(Blueprint):
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

    """

    VARIABLES = {
        'Class':
            {'type': str,
             'description': 'The troposphere class to create'},
        'Output':
            {'type': str,
             'description': 'The output to create'},
        'Properties':
            {'type': dict,
             'description': 'The list of propertie to use for the troposphere class'},
    }

    def setup_resource(self):
        template = self.template
        variables = self.get_variables()

        tclass = variables['Class']
        tprops = variables['Properties']
        output = variables['Output']

        klass = self.get_class('troposphere.' + tclass)

        # we need to do the following because of type conversion issues
        tprops_string = {}
        for variable, value in tprops.items():
          tprops_string[variable] = str(value)

        instance = klass.from_dict('ResourceRefName', tprops_string)

        template.add_resource(instance)
        template.add_output(Output(
            output,
            Description="The output",
            Value=Ref(instance)
        ))

    def create_template(self):
        """ Create the CFN template """
        self.add_cfn_description()
        self.setup_resource()

    def get_class(self, kls):
        parts = kls.split('.')
        module = ".".join(parts[:-1])
        m = __import__( module )
        for comp in parts[1:]:
            m = getattr(m, comp)            
        return m
