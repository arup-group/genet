import json
import os

import boto3


def get_google_directions_api_key(secret_name: str = None, region_name: str = None):
    """
    Extracts google directions api key from environmental variable or secrets manager
    :param secret_name:
    :param region_name:
    :return:
    """
    key = None
    if os.getenv("GOOGLE_DIR_API_KEY"):
        key = os.getenv("GOOGLE_DIR_API_KEY")
    elif secret_name and region_name:
        key = get_secret_as_dict(secret_name, region_name)
        if "key" in key:
            key = key["key"]
        elif "api_key" in key:
            key = key["api_key"]
    return key


def get_secret(secret_name, region_name):
    """
    Extracts api key from aws secrets manager
    :param secret_name:
    :param region_name:
    :return:
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


def get_secret_as_dict(secret_name, region_name):
    string_secret = get_secret(secret_name, region_name)
    if string_secret is not None:
        return json.loads(string_secret)
    else:
        return {}
