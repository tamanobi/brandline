from flask import Flask, request, redirect, session, url_for, render_template
import requests
import os
from jose import jwt
from jose.exceptions import ExpiredSignatureError
from redis_component import get_client
from requests_oauthlib import OAuth2Session
from linenotification import notify

app = Flask(__name__)

CHANNEL_ID = os.environ["LINE_LOGIN_CLIENT_ID"]
CLIENT_ID = os.environ["LINE_NOTIFY_CLIENT_ID"]
CLIENT_SECRET = os.environ["LINE_NOTIFY_CLIENT_SECRET"]
FLASK_HOST = os.environ["FLASK_HOST"]
REDIRECT_URI = f"{FLASK_HOST}/notification/callback"
LINE_LOGIN_REDIRECT_URI = f"{FLASK_HOST}/login/line/callback"
LINE_LOGIN_SECRET = os.environ["LINE_LOGIN_SECRET"]
SECRET_KEY = os.environ["SECRET_KEY"]

app.secret_key = SECRET_KEY
app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
redis_client = get_client()


def generate_code() -> tuple[str, str]:
    import random
    import string
    import hashlib
    import base64

    rand = random.SystemRandom()
    code_verifier = ''.join(rand.choices(string.ascii_letters + string.digits, k=128))  # noqa

    code_sha_256 = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    b64 = base64.urlsafe_b64encode(code_sha_256)
    code_challenge = b64.decode('utf-8').replace('=', '')

    return (code_verifier, code_challenge)


def is_logged_in():
    if "id_token" not in session:
        return False

    id_token = session["id_token"]
    try:
        verify_jwt(id_token)
    except ExpiredSignatureError:
        del session["id_token"]
        return False

    return True


@app.route("/")
def home():
    login_url = url_for("login_line")
    if is_logged_in():
        name = session["name"]
        setting_url = url_for("settings")
    else:
        name = None
        setting_url = None
    return render_template("index.html", login_url=login_url, setting_url=setting_url, name=name)


@app.route('/login/line')
def login_line():
    scope = ["profile", "openid"]
    redirect_uri = LINE_LOGIN_REDIRECT_URI
    line = OAuth2Session(CHANNEL_ID, scope=scope, redirect_uri=redirect_uri)
    code_verifier, code_challenge = generate_code()
    authorization_url, state = line.authorization_url("https://access.line.me/oauth2/v2.1/authorize", code_challenge=code_challenge, code_challenge_method="S256")  # noqa
    session["oauth_state"] = state
    session["code_verifier"] = code_verifier
    return redirect(authorization_url)


@app.route('/login/line/callback')
def login_line_callback():
    try:
        oauth_state = session["oauth_state"]
        code_verifier = session["code_verifier"]
        del session["code_verifier"]
        del session["oauth_state"]
    except Exception as e:
        print(f"key がなかったりして不正: {type(e)}{str(e)}")
        return redirect(url_for("home"))


    line = OAuth2Session(CHANNEL_ID, redirect_uri=LINE_LOGIN_REDIRECT_URI, state=oauth_state)  # noqa
    secure_url = request.url.replace('http://', 'https://', 1)
    token = line.fetch_token("https://api.line.me/oauth2/v2.1/token", client_secret=LINE_LOGIN_SECRET, authorization_response=secure_url, code_verifier=code_verifier)  # noqa

    session["token"] = token
    """
    {
      "access_token": "bNl4YEFPI/hjFWhTqexp4MuEw5YPs...",
      "expires_in": 2592000,
      "id_token": "eyJhbGciOiJIUzI1NiJ9...",
      "refresh_token": "Aa1FdeggRhTnPNNpxr8p",
      "scope": "profile",
      "token_type": "Bearer"
    }
    """
    id_token = token["id_token"]
    access_token = token["access_token"]
    refresh_token = token["refresh_token"]
    if not verify_jwt(id_token):
        raise ValueError

    userinfo = requests.post("https://api.line.me/oauth2/v2.1/userinfo", headers={"Authorization": f"Bearer {access_token}"}).json()  # noqa
    sub = userinfo["sub"]
    name = userinfo["name"]
    redis_client.set(f"brandline:login:{sub}:name", name)  # noqa
    redis_client.set(f"brandline:login:{sub}:access_token", access_token)  # noqa
    redis_client.set(f"brandline:login:{sub}:refresh_token", refresh_token)  # noqa
    session.permanent = True
    session["access_token"] = access_token
    session["refresh_token"] = refresh_token
    session["name"] = name
    session["sub"] = sub
    session["id_token"] = id_token
    return redirect(url_for("settings"))


def is_access_token_active(token: str):
    """notification の アクセストークンが有効化どうか調べる"""
    if not isinstance(token, str):
        raise ValueError(f"token が str じゃないよ: {type(token)} だったよ")
    status_url = "https://notify-api.line.me/api/status"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(status_url, headers=headers)
    print(res.json())
    # {"status":200,"message":"ok","target":"foobar"}
    return res.json()["status"] == 200


@app.route("/settings")
def settings():
    if not is_logged_in():
        print("/settings はログイン必須")
        return redirect(url_for("home"))

    try:
        id_token = verify_jwt(session["id_token"])
    except ExpiredSignatureError:
        return redirect(url_for("home"))

    sub = session["sub"]
    maybe_token = redis_client.get(f"brandline:notification:{sub}:access_token")
    already_set = False
    if maybe_token is not None:
        if is_access_token_active(maybe_token.decode("utf-8")):
            already_set = True
        else:
            print("アクセストークンがなんらかの理由で無効化されている状態")
            # アクセストークンがなんらかの理由で無効化されている状態
            redis_client.delete(f"brandline:notification:{sub}:access_token")
            redis_client.srem("brandline:notification:sub", sub)  # 通知リストからも削除
    else:
        print("値が取得できなった。maybe_token が None だよ")

    enable_url = url_for("notification_enable")
    return render_template("settings.html", enable_url=enable_url, name=session["name"], already_set=already_set)


@app.route('/notification/enable')
def notification_enable():
    """通知を有効化する"""
    # LINE Notifyの認証URLを生成
    notification = OAuth2Session(CLIENT_ID, scope=["notify"], redirect_uri=REDIRECT_URI)
    url, state = notification.authorization_url("https://notify-bot.line.me/oauth/authorize")  # noqa
    return redirect(url)


@app.route('/notification/callback')
def notification_callback():
    # コールバックから認証コードを取得
    code = request.args.get('code')

    # アクセストークンを取得
    token_url = "https://notify-bot.line.me/oauth/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    response = requests.post(token_url, headers=headers, data=data)
    if response.status_code == 200:
        access_token = response.json().get("access_token")

        sub = session["sub"]
        redis_client.set(f"brandline:notification:{sub}:access_token", access_token)
        redis_client.sadd("brandline:notification:sub", sub)

        text = "登録ありがとうございます。HERMES の商品が発売されたら報告します"
        notify(access_token, text, ignore_exception=False)
        return redirect(url_for('settings'))
    else:
        return "アクセストークンの取得に失敗しました。もう一度試してください"


def verify_jwt(encoded_jwt: str) -> dict:
    return jwt.decode(encoded_jwt, LINE_LOGIN_SECRET, algorithms=["HS256"], audience=CHANNEL_ID, issuer="https://access.line.me")  # noqa


if __name__ == "__main__":
    app.run(debug=True)
