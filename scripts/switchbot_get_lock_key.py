#!python
import os.path
import getpass
import urllib.parse
import sys
import subprocess

from multiprocessing.connection import Listener, Client

from switchbot.util import internal_api
from switchbot.api_config import SWITCHBOT_APP_COGNITO_POOL, SWITCHBOT_COGNITO_WEB_UI_URL


desktop_handler = """[Desktop Entry]
Name=SwitchBot Auth Client
Exec={} --auth-response %u
NoDisplay=true
Type=Application
Terminal=false
MimeType=x-scheme-handler/switchbot;
"""
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

    applications_dir = os.path.expanduser("~/.local/share/applications/")
    handler_path = os.path.join(applications_dir, "switchbot.desktop")
    try:
        print("Registering switchbot:// url handler")
        with open(handler_path, "w+") as f:
            f.write(desktop_handler.format(os.path.realpath(sys.argv[0])))
        subprocess.call(["update-desktop-database", applications_dir])

        print("Opening auth page")
        query_str = urllib.parse.urlencode({
            "response_type": "token",
            "client_id": SWITCHBOT_APP_COGNITO_POOL['AppClientId'],
            "redirect_uri": "switchbot://callback",
            "identity_provider": "COGNITO"
        })
        subprocess.call(["open", SWITCHBOT_COGNITO_WEB_UI_URL + "?" + query_str])

        print("Waiting for the auth response.")
        listener = Listener(address)

        conn = listener.accept()
        url = urllib.parse.urlparse(conn.recv())
        query: dict = urllib.parse.parse_qs(url.fragment)
        get_key(sys.argv[2], query["access_token"][0])
    except KeyboardInterrupt:
        # Cleanup after keyboard interrupt
        pass

    if os.path.isfile(handler_path):
        print("Removing switchbot:// url handler")
        os.remove(handler_path)
        subprocess.call(["update-desktop-database", applications_dir])


def get_key(mac_address, auth_token):
    try:
        result = internal_api.retrieve_encryption_key(mac_address, auth_token)
    except RuntimeError as e:
        print(e)
        exit(1)

    print("Key ID: " + result["key_id"])
    print("Encryption key: " + result["encryption_key"])


def handle_auth_response():
    conn = Client(address)
    conn.send(sys.argv[2])
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--auth-response':
        handle_auth_response()
    elif len(sys.argv) > 1 and sys.argv[1] == '--web-auth':
        web_auth()
    else:
        cli_auth()
