import logging
import requests
import hashlib


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
fmt_text = "%(asctime)s:%(name)s:%(levelname)s:%(message)s:%(line_text)s"
fmt = logging.Formatter(fmt_text)
sh = logging.StreamHandler()
sh.setFormatter(fmt)
logger.addHandler(sh)


def digest(msg: str):
    return hashlib.sha3_224(msg.encode("utf-8")).hexdigest()


def notify(access_token: str, message: str, ignore_exception=True):
    data = {"message": message}
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    try:
        extra = {"line_text": message.replace("\n", "<br>")}
        logger.info("%s 宛にメッセージを送りました", digest(access_token), extra=extra)
        requests.post("https://notify-api.line.me/api/notify", headers=headers, data=data)  # noqa
    except Exception:
        if ignore_exception:
            pass
        else:
            raise

