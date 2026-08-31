import logging
import os
import time
import redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedisClient:
    _instance = None  # משתנה מחלקה שישמור את המופע היחיד

    def __new__(cls, *args, **kwargs):
        # מנגנון Singleton: אם המופע כבר קיים, מחזירים אותו מיד בלי ליצור חדש!
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # מוודא שהאתחול והחיבור לרדיס ירוצו פעם אחת בלבד בכל חיי האפליקציה
        if getattr(self, '_initialized', False):
            return

        self.host = os.getenv('REDIS_HOST', 'localhost')
        self.port = int(os.getenv('REDIS_PORT', 6379))
        self.password = os.getenv('REDIS_PASSWORD', '2W6BjjAvv5')

        self.client = self._connect()
        self._initialized = True

    def _connect(self):
        for i in range(10):
            try:
                r = redis.Redis(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    decode_responses=True
                )
                r.ping()
                logger.info(f"Successfully connected to Redis at {self.host}:{self.port}")
                return r
            except Exception as e:
                logger.warning(f"Attempt {i + 1}/10 failed to connect to Redis: {e}")
                time.sleep(2)

        raise ConnectionError("Could not connect to Redis after 10 attempts.")

    def exists(self, key):
        return self.client.exists(key)

    def get(self, key):
        return self.client.get(key)

    def set(self, key, value):
        return self.client.set(key, value)

    def __getattr__(self, name):
        """
        קסם של פייתון: כל פקודה שתפעיל על האובייקט (כמו hset, get, exists וכו')
        שלא קיימת במחלקה הזו, תועבר אוטומטית לאובייקט הרדיס הפנימי (self.client).
        """
        return getattr(self.client, name)


# יוצרים מופע גלובלי שאפשר לייבא בראש שקט
r= RedisClient()