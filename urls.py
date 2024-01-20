import os
import requests
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def shorten_url(target: str) -> str | None:
    try:
        return shorten_url_core(target)
    except Exception as e:
        logging.exception(e)
        return None


def shorten_url_core(target: str) -> str:
    token = os.environ["TINYURL_TOKEN"]
    endpoint = f"https://api.tinyurl.com/create?api_token={token}"
    """サンプル

    {'code': 0,
 'data': {'alias': '7u7nb6ua',
          'analytics': {'enabled': True, 'public': False},
          'archived': False,
          'created_at': '2024-01-20T03:46:19+00:00',
          'deleted': False,
          'domain': 'tinyurl.com',
          'expires_at': None,
          'tags': [],
          'tiny_url': 'http://tinyurl.com/7u7nb6ua',
          'url': 'https://www.hermes.com/jp/ja/product/%E3%83%90%E3%83%83%E3%82%B0-%E3%80%8A%E3%83%9C%E3%83%AA%E3%83%BC%E3%83%891923%E3%80%8B-45-%E3%83%AC%E3%83%BC%E3%82%B7%E3%83%B3%E3%82%B0-H078595CKAA/'},
 'errors': []}
    """
    data = {"url": target}

    r = requests.post(endpoint, data=data)
    return r.json()["data"]["tiny_url"]

