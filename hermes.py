import requests
from bs4 import BeautifulSoup
import json
import os

import redis_component
from redis_component import get_client, get_users, get_user_access_token, is_new_hermes_bags, add_notified_hermes_bags, reset_notified_hermes_bags  # noqa
from linenotification import notify
from tenacity import retry, stop_after_attempt, wait_fixed
import logging
import urllib.parse
import urls
from typing import Tuple


logger = logging.getLogger(__name__)
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
logger.setLevel(logging.DEBUG)
logger.addHandler(sh)


def create_message(notifying_items: list[Tuple[str, str]], category_url: str) -> str:  # noqa
    """送信するメッセージを作成する"""

    item_messages = []
    for title, url in notifying_items:
        shorten_url = urls.shorten_url(url)
        # URL が長すぎると LINE 側から省略されてしまうことがあるため 短縮 URL を使う
        if shorten_url:
            item_message = f"""{title}\n{shorten_url}"""
        else:
            # なんらかの理由で短縮に失敗した場合長い URL を使う
            item_message = f"""{title}\n{url}"""
        item_messages.append(item_message)
    header = "\n"
    footer = f"\n\n◆商品一覧はこちら\n{category_url}"

    return header + "\n\n".join(item_messages) + footer


def extract_items_by_json_str(json_str: str):
    categories = json.loads(json_str)
    """
    categories の中身はこんな感じ。

    "G.json.https://bck.hermes.com/products?available_online=false&category=WOMENBAGSBAGSCLUTCHES&locale=jp_ja&pagesize=48&sort=relevance": {  # noqa
        "body": {
          "total": 5,
          "products": {
            "items": [
              {
                "sku": "H084623CKAB",
    """
    category = categories["G.json.https://bck.hermes.com/products?available_online=false&category=WOMENBAGSBAGSCLUTCHES&locale=jp_ja&pagesize=48&sort=relevance"]  # noqa
    """
    a の中身はこんな感じ

    "body": {
        "total": 5,
        "products": {
          "items": [
            {
              "sku": "H084623CKAB",
              "title": "メッセンジャー 《エールバッグ》 39",
    """
    return category["body"]["products"]["items"]


def is_local():
    return os.environ.get("APP_ENV") == "local"


def is_active():
    if is_local():
        return True
    return redis_component.is_active_notifications()


@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def job():
    if not is_active():
        print("おしまい")
        return

    proxy = os.environ["PROXY_URL"]
    proxies = {
        'http': f"http://{proxy}",
        'https': f"http://{proxy}",
    }

    category_url = "https://www.hermes.com/jp/ja/category/women/bags-and-small-leather-goods/bags-and-clutches/"  # noqa
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"  # noqa
    }
    res = requests.get(category_url, headers=headers, proxies=proxies)
    res.raise_for_status()
    logger.info("HERMES のカテゴリページにアクセス成功: %s", category_url)
    soup = BeautifulSoup(res.text, "html.parser")
    script = soup.find(id="hermes-state")
    if script is None:
        raise ValueError("hermes-state が見つからなかった")
    logger.info("HERMES のカテゴリページで商品データにアクセス成功: %s", category_url)

    items = extract_items_by_json_str(script.text)

    all_items = []
    notifying_items = []
    for item in items:
        sku, title = item["sku"], item["title"]
        product_url = item["url"]
        # カタログページに表示されているものだけを表示する場合, 有効化する
        # product_exists = (soup.find(id=f"grid-product-{sku}") is not None)
        # if product_exists:

        # ja_url = f"https://www.hermes.com/jp/ja/product/{sku}"
        percent_encoded = urllib.parse.quote(product_url)
        ja_url = f"https://www.hermes.com/jp/ja{percent_encoded}"
        all_items.append((title, ja_url))
        if is_new_hermes_bags(ja_url, sku):
            notifying_items.append((title, ja_url))
        add_notified_hermes_bags(ja_url, sku)
    # 洗い替え
    reset_notified_hermes_bags(all_items)

    if not notifying_items:
        logger.info("新着なしなのでスキップ。商品一覧: %s", str(all_items))
        return

    message = create_message(notifying_items, category_url)
    users = get_users()
    if is_local():
        test_user = os.environ.get("TEST_USER_SUB")
        if test_user:
            users = [test_user]
        else:
            logger.info("テストユーザーがいないため通知対象ユーザーを空にしました")
            users = []
    for user in users:
        access_token = get_user_access_token(user)
        if access_token:
            notify(access_token, message, ignore_exception=False)
        else:
            logger.info("アクセストークンがないのでユーザーをスキップします: user=%s", user)


if __name__ == "__main__":
    job()
