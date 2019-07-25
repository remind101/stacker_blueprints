from . import base


class RedisReplicationGroup(base.BaseReplicationGroup):
    def engine(self):
        return "redis"

    def get_engine_versions(self):
        return ["2.6.13", "2.8.19", "2.8.21", "2.8.22", "2.8.23", "2.8.24",
                "2.8.6", "3.2.4", "3.2.6", "3.2.10", "4.0.10", "5.0.0",
                "5.0.3", "5.0.4"]

    def get_parameter_group_family(self):
        return ["redis2.6", "redis2.8", "redis3.2", "redis4.0", "redis5.0"]
