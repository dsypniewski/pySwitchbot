#!python
import getpass
import urllib.parse
import sys
import webbrowser
import requests
import requests.auth

from multiprocessing.connection import Listener

from switchbot.util import internal_api, register_url_handler
from switchbot.api_config import SWITCHBOT_APP_COGNITO_POOL, SWITCHBOT_COGNITO_WEB_UI_URL

address = ('127.0.0.1', 6000)
REDIRECT_URI = "switchbot://callback"


def cli_auth():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <device_mac> <username>")
        exit(1)

    password = getpass.getpass()
    auth_token = internal_api.login(sys.argv[2], password)
    get_key(sys.argv[1], auth_token)


def web_auth():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} --web-auth <device_mac>")
        exit(1)

    try:
        print("Registering switchbot:// url handler")
        register_url_handler.register("switchbot", address)

        print("Opening auth page")
        # Chrome on Windows has 2048-character limit for custom URL handlers
        # AWS token responses are over that limit hence using code type and then exchanging it
        query_str = urllib.parse.urlencode({
            "response_type": "code",
            "client_id": SWITCHBOT_APP_COGNITO_POOL['AppClientId'],
            "redirect_uri": REDIRECT_URI,
            "identity_provider": "COGNITO",
        })
        webbrowser.open_new_tab(SWITCHBOT_COGNITO_WEB_UI_URL + "oauth2/authorize?" + query_str)

        print("Waiting for the auth response.")
        listener = Listener(address)

        conn = listener.accept()
        url = urllib.parse.urlparse(conn.recv())
        query: dict = urllib.parse.parse_qs(url.query)
        access_token = get_access_token_from_code(query["code"][0])
        get_key(sys.argv[2], access_token)
    except KeyboardInterrupt:
        # Cleanup after keyboard interrupt
        pass

    register_url_handler.cleanup("switchbot")


def get_access_token_from_code(code: str):
    token_url = f"{SWITCHBOT_COGNITO_WEB_UI_URL}oauth2/token"
    auth = requests.auth.HTTPBasicAuth(
        SWITCHBOT_APP_COGNITO_POOL["AppClientId"],
        SWITCHBOT_APP_COGNITO_POOL["AppClientSecret"]
    )

    params = {
        "grant_type": "authorization_code",
        "client_id": (SWITCHBOT_APP_COGNITO_POOL["AppClientId"]),
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    response = requests.post(token_url, auth=auth, data=params)

    return response.json()["access_token"]


def get_key(mac_address, auth_token):
    try:
        result = internal_api.retrieve_encryption_key(mac_address, auth_token)
    except RuntimeError as e:
        print(e)
        exit(1)

    print("Key ID: " + result["key_id"])
    print("Encryption key: " + result["encryption_key"])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--web-auth':
        web_auth()
    else:
        cli_auth()
