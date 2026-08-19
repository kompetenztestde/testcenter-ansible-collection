from typing import Optional, List

import requests

from ansible.module_utils.basic import AnsibleModule


def get_authenticated_session(
    baseurl: str, auth_user: str, auth_password: str
) -> requests.Session:
    s = requests.Session()

    # authenticate with testcenter
    auth_payload = {
        "name": auth_user,
        "password": auth_password,
    }
    r = s.put(baseurl + "/api/session/admin", json=auth_payload)
    r.raise_for_status()

    auth_token = r.json()["token"]
    s.headers.update({"AuthToken": auth_token})
    return s


def handle_requests_exception(
    e: requests.exceptions.RequestException,
    module: AnsibleModule,
    msg: str,
    result: dict,
):
    module.fail_json(
        msg=msg,
        status_code=e.response.status_code if e.response else None,
        server_msg=e.response.text if e.response else None,
        exception=e,
        **result,
    )


def get_users(s: requests.Session, baseurl: str) -> List[dict]:
    r = s.get(baseurl + "/api/users")
    r.raise_for_status()
    return r.json()



def get_user_id(users: List[dict], name: str) -> Optional[int]:
    filtered_users = [user["id"] for user in users if user["name"] == name]
    return filtered_users[0] if filtered_users else None
