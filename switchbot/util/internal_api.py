import base64
import hashlib
import hmac
import json

import boto3
import requests

from ..api_config import SWITCHBOT_APP_API_BASE_URL, SWITCHBOT_APP_COGNITO_POOL
from ..const import (
    SwitchbotAccountConnectionError,
    SwitchbotAuthenticationError,
)


def login(username: str, password: str) -> str:
    msg = bytes(username + SWITCHBOT_APP_COGNITO_POOL["AppClientId"], "utf-8")
    secret_hash = base64.b64encode(
        hmac.new(
            SWITCHBOT_APP_COGNITO_POOL["AppClientSecret"].encode(),
            msg,
            digestmod=hashlib.sha256,
        ).digest()
    ).decode()

    cognito_idp_client = boto3.client(
        "cognito-idp", region_name=SWITCHBOT_APP_COGNITO_POOL["Region"]
    )
    try:
        auth_response = cognito_idp_client.initiate_auth(
            ClientId=SWITCHBOT_APP_COGNITO_POOL["AppClientId"],
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
                "SECRET_HASH": secret_hash,
            },
        )
    except cognito_idp_client.exceptions.NotAuthorizedException as err:
        raise SwitchbotAuthenticationError(
            f"Failed to authenticate: {err}"
        ) from err
    except Exception as err:
        raise SwitchbotAuthenticationError(
            f"Unexpected error during authentication: {err}"
        ) from err

    if (
            auth_response is None
            or "AuthenticationResult" not in auth_response
            or "AccessToken" not in auth_response["AuthenticationResult"]
    ):
        raise SwitchbotAuthenticationError("Unexpected authentication response")
    return auth_response["AuthenticationResult"]["AccessToken"]


def retrieve_encryption_key(device_mac: str, access_token: str):
    """Retrieve lock key from internal SwitchBot API."""
    device_mac = device_mac.replace(":", "").replace("-", "").upper()
    try:
        key_response = requests.post(
            url=SWITCHBOT_APP_API_BASE_URL + "/developStage/keys/v1/communicate",
            headers={"authorization": access_token},
            json={
                "device_mac": device_mac,
                "keyType": "user",
            },
            timeout=10,
        )
    except requests.exceptions.RequestException as err:
        raise SwitchbotAccountConnectionError(
            f"Failed to retrieve encryption key from SwitchBot Account: {err}"
        ) from err
    if key_response.status_code > 299:
        raise SwitchbotAuthenticationError(
            f"Unexpected status code returned by SwitchBot Account API: {key_response.status_code}"
        )
    key_response_content = json.loads(key_response.content)
    if key_response_content["statusCode"] != 100:
        raise SwitchbotAuthenticationError(
            f"Unexpected status code returned by SwitchBot API: {key_response_content['statusCode']}"
        )

    return {
        "key_id": key_response_content["body"]["communicationKey"]["keyId"],
        "encryption_key": key_response_content["body"]["communicationKey"]["key"],
    }