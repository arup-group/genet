from unittest import mock
import os
import boto3
import pytest

from genet.utils import secrets_vault

# pytest's expected error mechanism ('raises' context mgr) is not intuitive and I want to make it clearer
expected_error = pytest.raises


def test_gets_api_key_with_secrets_manager_string_key(mocker):
    mocker.patch.object(secrets_vault, 'get_secret_as_dict', return_value={'key': 'awesome_key'})
    key = secrets_vault.get_google_directions_api_key(secret_name='secret', region_name='region')
    assert key == "awesome_key"


def test_gets_api_key_with_secrets_manager_string_api_key(mocker):
    mocker.patch.object(secrets_vault, 'get_secret_as_dict', return_value={'api_key': 'awesome_key'})
    key = secrets_vault.get_google_directions_api_key(secret_name='secret', region_name='region')
    assert key == "awesome_key"


def test_gets_api_key_with_environmental_variable():
    try:
        os.environ["GOOGLE_DIR_API_KEY"] = "awesome_key"
        key = secrets_vault.get_google_directions_api_key()
        assert key == "awesome_key"
    except Exception as e:
        raise e
    finally:
        del os.environ["GOOGLE_DIR_API_KEY"]


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


def test_swallows_not_found_exception_when_retrieving_unknown_secret():
    # ugly hack: boto3 client subclass exceptions seem to be dynamically generated, so cannot be imported, instantiated
    # or mocked in the usual way, hence the following abomination, which makes a real client solely in order to access
    # the 'exceptions' attribute in lieu of a simple import, create an exception of the right kind, and then copy the
    # real client 'exceptions' attribute on to the mock client object
    #
    # see https://github.com/boto/boto3/issues/1470 and https://github.com/boto/boto3/issues/1262 for more detail
    real_client = boto3.client('secretsmanager', 'eu-west-1')
    not_found_exception = real_client.exceptions.ResourceNotFoundException({}, 'Boom!')
    with mock.patch('boto3.client') as mock_client:
        # exception handler block expects the client to have the definition of ResourceNotFoundException
        mock_client.return_value.exceptions = real_client.exceptions
        mock_client.return_value.get_secret_value.side_effect = not_found_exception

        secret = secrets_vault.get_secret("some-project/some-credentials", region_name='some-region')

        mock_client.return_value.get_secret_value.assert_called_once()
    assert secret is None


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


def test_transforms_not_found_secret_value_to_empty_dict():
    real_client = boto3.client('secretsmanager', 'eu-west-1')
    not_found_exception = real_client.exceptions.ResourceNotFoundException({}, 'Boom!')
    with mock.patch('boto3.client') as mock_client:
        # exception handler block expects the client to have the definition of ResourceNotFoundException
        mock_client.return_value.exceptions = real_client.exceptions
        mock_client.return_value.get_secret_value.side_effect = not_found_exception

        secret_dict = secrets_vault.get_secret_as_dict("some-project/some-credentials", region_name='some-region')

        mock_client.return_value.get_secret_value.assert_called_once()
    assert secret_dict == {}


def test_propagates_general_exceptions_from_secrets_manager_client():
    real_client = boto3.client('secretsmanager', 'eu-west-1')
    internal_service_error = real_client.exceptions.InternalServiceError({}, 'Boom!')
    with mock.patch('boto3.client') as mock_client:
        # exception handler block expects the client to have the definition of InternalServiceError
        mock_client.return_value.exceptions = real_client.exceptions
        mock_client.return_value.get_secret_value.side_effect = internal_service_error

        with expected_error(real_client.exceptions.InternalServiceError) as exc_info:
            secrets_vault.get_secret("some-project/some-credentials", region_name='some-region')
    assert exc_info.value is internal_service_error


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
