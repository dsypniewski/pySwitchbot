#!python
import getpass
import urllib.parse
import sys
import webbrowser

from multiprocessing.connection import Listener

from switchbot.util import internal_api, register_url_handler
from switchbot.api_config import SWITCHBOT_APP_COGNITO_POOL, SWITCHBOT_COGNITO_WEB_UI_URL

address = ('127.0.0.1', 6000)


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
        query_str = urllib.parse.urlencode({
            "response_type": "token",
            "client_id": SWITCHBOT_APP_COGNITO_POOL['AppClientId'],
            "redirect_uri": "switchbot://callback",
            "identity_provider": "COGNITO"
        })
        webbrowser.open_new_tab(SWITCHBOT_COGNITO_WEB_UI_URL + "?" + query_str)

        print("Waiting for the auth response.")
        listener = Listener(address)

        conn = listener.accept()
        url = urllib.parse.urlparse(conn.recv())
        query: dict = urllib.parse.parse_qs(url.fragment)
        get_key(sys.argv[2], query["access_token"][0])
    except KeyboardInterrupt:
        # Cleanup after keyboard interrupt
        pass

    register_url_handler.cleanup("switchbot")


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
