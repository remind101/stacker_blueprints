from stacker.blueprints.base import Blueprint

from troposphere import ecr


class Repositories(Blueprint):

    VARIABLES = {
        "Repositories": {
            "type": list,
            "description": "A list of repository names to create."
        }
    }

    def create_template(self):
        t = self.template
        variables = self.get_variables()

        for repo in variables["Repositories"]:
            t.add_resource(
                ecr.Repository(
                    "%sRepository" % repo,
                    RepositoryName=repo,
                )
            )
