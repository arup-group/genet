from unittest import mock
from genet.utils import secrets_vault


def test_finds_text_secret_when_present_in_secrets_manager():
    secrets_manager_response = {
        "Name": "some-project/some-credentials",
        "VersionId": "95bda51c-1451-4f48-8171-e287518d8299",
        "SecretString": "{\"api_key\":\"abc123def456\"}",
        "VersionStages": ["AWSCURRENT"],
        "CreatedDate": 1534174155.103,
        "ARN": "arn:aws:secretsmanager:eu-west-1:275257401670:secret:some-project/some-credentials-uMUd5v"
    }
    with mock.patch('boto3.client') as mock_client:
        mock_client.return_value.get_secret_value.return_value = secrets_manager_response
        secret = secrets_vault.get_secret("some-project/some-credentials", region_name='some-region')
    assert secret == secrets_manager_response['SecretString']


def test_transforms_text_secret_to_dict():
    secrets_manager_response = {
        "Name": "some-project/some-credentials",
        "VersionId": "95bda51c-1451-4f48-8171-e287518d8299",
        "SecretString": "{\"api_key\":\"abc123def456\"}",
        "VersionStages": ["AWSCURRENT"],
        "CreatedDate": 1534174155.103,
        "ARN": "arn:aws:secretsmanager:eu-west-1:275257401670:secret:some-project/some-credentials-uMUd5v"
    }
    with mock.patch('boto3.client') as mock_client:
        mock_client.return_value.get_secret_value.return_value = secrets_manager_response
        secret = secrets_vault.get_secret_as_dict("some-project/some-credentials", region_name='some-region')
    assert secret == {'api_key': 'abc123def456'}


def test_finds_binary_secret_when_present_in_secrets_manager():
    secrets_manager_response = {
        "Name": "some-project/some-credentials",
        "VersionId": "95bda51c-1451-4f48-8171-e287518d8299",
        "SecretBinary": "bm93IHRoZW4gbWFyZHkgYnVt",
        "VersionStages": ["AWSCURRENT"],
        "CreatedDate": 1534174155.103,
        "ARN": "arn:aws:secretsmanager:eu-west-1:275257401670:secret:some-project/some-credentials-uMUd5v"
    }
    with mock.patch('boto3.client') as mock_client:
        mock_client.return_value.get_secret_value.return_value = secrets_manager_response
        secret = secrets_vault.get_secret("some-project/some-credentials", region_name='some-region')
    assert secret == secrets_manager_response['SecretBinary']


def test_transforms_binary_secret_to_dict():
    secrets_manager_response = {
        "Name": "some-project/some-credentials",
        "VersionId": "95bda51c-1451-4f48-8171-e287518d8299",
        "SecretBinary": "bm93IHRoZW4gbWFyZHkgYnVt",
        "VersionStages": ["AWSCURRENT"],
        "CreatedDate": 1534174155.103,
        "ARN": "arn:aws:secretsmanager:eu-west-1:275257401670:secret:some-project/some-credentials-uMUd5v"
    }
    with mock.patch('boto3.client') as mock_client:
        mock_client.return_value.get_secret_value.return_value = secrets_manager_response
        secret = secrets_vault.get_secret("some-project/some-credentials", region_name='some-region')
    assert secret == "bm93IHRoZW4gbWFyZHkgYnVt"
