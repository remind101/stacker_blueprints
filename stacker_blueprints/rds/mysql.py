from .base import MasterInstance, ReadReplica


class MySQLMixin(object):
    def engine(self):
        return "MySQL"

    def get_engine_versions(self):
        return [
            '5.1.73a', '5.1.73b',
            '5.5.40', '5.5.40a', '5.5.40b', '5.5.41', '5.5.42', '5.5.46',
            '5.6.19a', '5.6.19b', '5.6.21', '5.6.21b', '5.6.22', '5.6.23',
            '5.6.27', '5.6.29',
            '5.7.10', '5.7.11'
        ]

    def get_db_families(self):
        return [
            "mysql5.1",
            "mysql5.5",
            "mysql5.6",
            "mysql5.7",
        ]


class MasterInstance(MySQLMixin, MasterInstance):
    pass


class ReadReplica(MySQLMixin, ReadReplica):
    pass
