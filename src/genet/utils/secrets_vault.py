import json
import os
from typing import Optional

import boto3


def get_google_directions_api_key(
    secret_name: Optional[str] = None, region_name: Optional[str] = None
) -> Optional[str]:
    """Extracts google directions api key from environmental variable or secrets manager.

    Args:
        secret_name (Optional[str], optional):
            If given and API key is not an environment variable, will search for the secret in the AWS secrets manager.
            Defaults to None.
        region_name (Optional[str], optional):
            If given and API key is not an environment variable, will search for the secret in the given AWS region account.
            Defaults to None.

    Returns:
        Optional[str]: Google API key, if there is one to find.
    """
    key: Optional[str] = os.getenv("GOOGLE_DIR_API_KEY")

    if key is None and (secret_name is not None and region_name is not None):
        key_dict = get_secret_as_dict(secret_name, region_name)
        if "key" in key_dict:
            key = key_dict["key"]
        elif "api_key" in key_dict:
            key = key_dict["api_key"]
    return key


def get_secret(secret_name: str, region_name: str) -> str:
    """Extracts api key from aws secrets manager.

    Args:
        secret_name (str):
            Will search for the secret in the AWS secrets manager.
        region_name (str):
            Will search for the secret in the given AWS region account.

    Returns:
        str: JSON response string.

    """
    client = boto3.client("secretsmanager", region_name=region_name)

    print("Looking for secret '{}' in the vault".format(secret_name))

    try:
        response = client.get_secret_value(SecretId=secret_name)
    except client.exceptions.ResourceNotFoundException:
        return None
    if "SecretString" in response:
        print("Found string secret for '{}'".format(secret_name))
        return response["SecretString"]
    else:
        print("Found binary secret for '{}'".format(secret_name))
        return response["SecretBinary"]


def get_secret_as_dict(secret_name: str, region_name: str) -> dict:
    string_secret = get_secret(secret_name, region_name)
    if string_secret is not None:
        return json.loads(string_secret)
    else:
        return {}
