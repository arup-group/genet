import boto3
import json


def get_secret(secret_name, region_name):

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
