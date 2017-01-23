from .base import MasterInstance, ReadReplica


class MySQLMixin(object):
    def engine(self):
        return "MySQL"


class MasterInstance(MySQLMixin, MasterInstance):
    pass


class ReadReplica(MySQLMixin, ReadReplica):
    pass
