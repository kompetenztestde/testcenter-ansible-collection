from ansible_collections.kompetenztestde.testcenter.plugins.module_utils import (
    testcenter,
)

from requests.exceptions import RequestException
from requests import Response, Session
from unittest.mock import MagicMock, patch


USERS_RESPONSE = b"""[
    {
        "name": "super",
        "id": "1",
        "email": null,
        "isSuperadmin": true
    },
    {
        "name": "super2",
        "id": "2",
        "email": null,
        "isSuperadmin": false
    }
]"""


@patch("requests.put")
def test_get_authenticated_session(requests_patch):
    response = Response()
    response.status_code = 200
    response._content = b'{"token": "abcdef"}'
    response.encoding = "utf-8"

    requests_patch.return_value = response

    session = testcenter.get_authenticated_session(
        "https://tc.example.com", "super", "user123"
    )
    assert session.headers["AuthToken"] == "abcdef"


def test_handle_requests_exception():
    module = MagicMock()

    response = Response()
    response.status_code = 400
    response._content = b"Testcenter Error"
    response.encoding = "utf-8"
    e = RequestException(response=response)
    testcenter.handle_requests_exception(e, module, "Test Message", {})

    module.fail_json.assert_called_once_with(
        msg="Test Message", status_code=400, server_msg="Testcenter Error", exception=e
    )


def test_get_users():
    response = Response()
    response.status_code = 200
    response._content = USERS_RESPONSE
    response.encoding = "utf-8"

    session = Session()
    session.get = MagicMock(return_value=response)
    users = testcenter.get_users(session, "https://tc.example.com")
    session.get.assert_called_once_with("https://tc.example.com/api/users")
    assert len(users) == 2


def test_get_user_id_included():
    users = [
        {"name": "super", "id": "1", "email": None, "isSuperadmin": True},
        {"name": "super2", "id": "2", "email": None, "isSuperadmin": False},
    ]
    user_id = testcenter.get_user_id(users, "super")
    assert user_id == "1"


def test_get_user_id_not_included():
    users = [
        {"name": "super", "id": "1", "email": None, "isSuperadmin": True},
        {"name": "super2", "id": "2", "email": None, "isSuperadmin": False},
    ]
    user_id = testcenter.get_user_id(users, "super3")
    assert user_id is None
