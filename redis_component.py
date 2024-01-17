import os
import redis
from typing import Tuple

REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = 33042
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")


client = None


def get_client():
    global client
    if client:
        return client
    client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, ssl=True)  # noqa
    return client


def get_users():
    """通知を受け取りたいユーザ"""
    client = get_client()
    return [member.decode("utf-8") for member in client.smembers("brandline:notification:sub")]  # noqa


def get_user_access_token(user: str):
    client = get_client()
    data = client.get(f"brandline:notification:{user}:access_token")
    if data:
        return data.decode("utf-8")
    return None


KEY_BRANDLINE_HERMES_BAGS_AND_CLUTCHES_ALL = "brandline:hermes:bags-and-clutches:all"
KEY_BRANDLINE_HERMES_BAGS_AND_CLUTCHES = "brandline:hermes:bags-and-clutches"


def is_new_hermes_bags(ja_url, sku):
    key = KEY_BRANDLINE_HERMES_BAGS_AND_CLUTCHES
    client = get_client()
    exists_ja_url = client.sismember(key, ja_url)
    exists_sku = client.sismember(key, sku)
    return not (exists_ja_url or exists_sku)


def add_notified_hermes_bags(ja_url, sku):
    key = KEY_BRANDLINE_HERMES_BAGS_AND_CLUTCHES_ALL
    client = get_client()
    client.sadd(key, ja_url)
    client.sadd(key, sku)


def reset_notified_hermes_bags(items: list[Tuple[str, str]]):
    key = KEY_BRANDLINE_HERMES_BAGS_AND_CLUTCHES
    client = get_client()

    # lua script に書きかえたほうがいいかも
    with client.pipeline() as pipe:
        pipe.delete(key)
        for ja_url, sku in items:
            pipe.sadd(key, ja_url)
            pipe.sadd(key, sku)
        pipe.execute()
