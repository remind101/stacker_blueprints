from .base import MasterInstance, ReadReplica


class PostgresMixin(object):
    def engine(self):
        return "postgres"


class MasterInstance(PostgresMixin, MasterInstance):
    pass


class ReadReplica(PostgresMixin, ReadReplica):
    pass
