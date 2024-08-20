import redis

host = "39.104.6.97"
port = 6379
database = 13
password = "testadmin:Psh12345"


class RedisClient:
    client = None

    def __init__(self):
        if self.client is None:
            self.client = redis.Redis(host, port, database, password)

    def get_client(self):
        return self.client

    def get_str(self, key):
        if self.client.exists(key):
            return self.client.get(key).decode('utf-8')
        else:
            return None
