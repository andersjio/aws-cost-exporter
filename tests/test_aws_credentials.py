import os
from unittest import mock
import pytest
from aws_cost_exporter2 import set_credentials, __check_credentials

# Comment
@mock.patch.dict(os.environ, 
    {"AWS_ACCESS_KEY_ID": "SOME_AWS_ACCESS_KEY",
    "AWS_SECRET_ACCESS_KEY": "SOME_SECRET_VALUE",
    "REGION": "eu-test-region"})
def test_set_credentials_from_environment():
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, REGION = set_credentials()
    assert AWS_ACCESS_KEY_ID == "SOME_AWS_ACCESS_KEY"
    assert AWS_SECRET_ACCESS_KEY == "SOME_SECRET_VALUE"
    assert REGION == "eu-test-region"

# Should exit because 'REGION' have empty value set
@mock.patch.dict(os.environ, 
    {"AWS_ACCESS_KEY_ID": "SOME_AWS_ACCESS_KEY",
    "AWS_SECRET_ACCESS_KEY": "SOME_SECRET_VALUE",
    "REGION": "",})
def test_set_credentials_from_environment_one_empty_value_should_exit():
    with pytest.raises(SystemExit) as pytest_wrapped_e:
            set_credentials()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1


@mock.patch.dict(os.environ, 
    {"AWS_ACCESS_KEY_ID": "SOME_AWS_ACCESS_KEY",
    "AWS_SECRET_ACCESS_KEY": "SOME_SECRET_VALUE"})
# Should exit because 'REGION' is missing
def test_set_credentials_from_environment_one_missing_should_exit():
    with pytest.raises(SystemExit) as pytest_wrapped_e:
            set_credentials()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1
