from .base import MasterInstance, ReadReplica


class PostgresMixin(object):
    def engine(self):
        return "postgres"

    def get_engine_versions(self):
        return [
            '9.3.1', '9.3.2', '9.3.3', '9.3.5', '9.3.6', '9.3.9', '9.3.10',
            '9.3.12',
            '9.4.1', '9.4.4', '9.4.5', '9.4.7',
            '9.5.2',
        ]

    def get_db_families(self):
        return [
            "postgres9.3",
            "postgres9.4",
            "postgres9.5",
        ]


class MasterInstance(PostgresMixin, MasterInstance):
    pass


class ReadReplica(PostgresMixin, ReadReplica):
    pass
