import requests
from bs4 import BeautifulSoup
import json
import os

from redis_component import get_client, get_users, get_user_access_token, is_new_hermes_bags, add_notified_hermes_bags  # noqa
from linenotification import notify
from tenacity import retry, stop_after_attempt, wait_fixed
import logging


logger = logging.getLogger(__name__)
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
logger.setLevel(logging.DEBUG)
logger.addHandler(sh)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def job():
    client = get_client()
    if client.get("brandline:notifications:active").decode("utf-8") == "0":
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
    logger.info("status_code: %s", res.status_code)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    script = soup.find(id="hermes-state")
    if script is None:
        raise ValueError("hermes-state が見つからなかった")

    json_str = script.text
    # from pathlib import Path
    # json_str = Path("datahelmes.json").read_text()
    z = json.loads(json_str)
    a = z["G.json.https://bck.hermes.com/products?available_online=false&category=WOMENBAGSBAGSCLUTCHES&locale=jp_ja&pagesize=48&sort=relevance"]  # noqa
    items = a["body"]["products"]["items"]

    all_items = []
    notifying_items = []
    for item in items:
        sku, title = item["sku"], item["title"]
        # カタログページに表示されているものだけを表示する場合, 有効化する
        # product_exists = (soup.find(id=f"grid-product-{sku}") is not None)
        # if product_exists:
        ja_url = f"https://www.hermes.com/jp/ja/product/{sku}"
        all_items.append((title, ja_url))
        if is_new_hermes_bags(ja_url, sku):
            notifying_items.append((title, ja_url))
        add_notified_hermes_bags(ja_url, sku)

    if not notifying_items:
        print("新着なしなのでスキップ")
        return

    item_messages = []
    for title, url in notifying_items:
        item_message = f"""{title}\n{url}"""
        item_messages.append(item_message)
    header = "\n"
    footer = f"\n\n◆商品一覧はこちら\n{category_url}"
    message = header + "\n\n".join(item_messages) + footer

    for user in get_users():
        access_token = get_user_access_token(user)
        if access_token:
            notify(access_token, message, ignore_exception=False)
        else:
            print("skip", user)


    """
    "body": {
        "total": 5,
        "products": {
          "items": [
            {
              "sku": "H084623CKAB",
              "title": "メッセンジャー 《エールバッグ》 39",
    """
    # from pprint import pprint
    # print(json.dumps(a))
    # pprint(a)
    """
    "G.json.https://bck.hermes.com/products?available_online=false&category=WOMENBAGSBAGSCLUTCHES&locale=jp_ja&pagesize=48&sort=relevance": {  # noqa
        "body": {
          "total": 5,
          "products": {
            "items": [
              {
                "sku": "H084623CKAB",
    """
    # print(json.dumps(z))
    # hermes-state


if __name__ == "__main__":
    job()
