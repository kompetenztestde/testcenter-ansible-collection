#!/usr/bin/python

from __future__ import absolute_import, division, print_function
from typing import Optional

import requests

__metaclass__ = type

DOCUMENTATION = r"""
---
module: testcenter_user

short_description: Manage IQB Testcenter admin users

version_added: "1.0.0"

description: Add, edit or remove IQB Testcenter admin users

options:
    baseurl:
        description: Base url of the testcenter instance
        required: true
        type: str
    auth_user:
        description: User to authenticate with
        required: true
        type: str
    auth_password:
        description: Password to authenticate with
        required: true
        type: str
    username:
        description: Username of the user
        required: true
        type: str
    state:
        description: State of the user
        default: present
        choices:
            - present
            - absent
    password:
        description: Password of the user
        type: str
    superadmin:
        description: Is the user a superadmin user
        type: bool
        default: false

author:
    - Oskar Jauch (oskar.jauch@uni-jena.de)
"""

EXAMPLES = r"""
# create a new user
- name: Create new user
  kompetenztestde.testcenter.testcenter_user:
    baseurl: https://example.com
    auth_user: super
    auth_password: super123
    username: newuser
    password: newpassword
    state: present

# delete an existing user
- name: Delete an existing user
  kompetenztestde.testcenter.testcenter_user:
    baseurl: https://example.com
    auth_user: super
    auth_password: super123
    username: newuser
    state: absent

# change user password
- name: Change user password
  kompetenztestde.testcenter.testcenter_user:
    baseurl: https://example.com
    auth_user: super
    auth_password: super123
    username: super
    password: newpassword
    state: present
"""

RETURN = r"""
# These are examples of possible return values, and in general should use other names for return values.
user_id:
    description: ID of the user created, edited or removed
    type: int
    sample: 1
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.kompetenztestde.testcenter.plugins.module_utils.testcenter import (
    get_authenticated_session,
    handle_requests_exception,
    get_users,
)


def set_user_password(
    s: requests.Session,
    baseurl: str,
    username: str,
    password: str,
    user_id: int,
    check_mode: bool = False,
) -> bool:
    auth_payload = {
        "name": username,
        "password": password,
    }
    r = requests.put(baseurl + "/api/session/admin", json=auth_payload)
    if r.status_code != 200:
        # password differs -> change it
        password_change_payload = {"p": password}
        if not check_mode:
            r = s.patch(
                baseurl + f"/api/user/{user_id}/password",
                json=password_change_payload,
            )
            r.raise_for_status()
        return True
    return False


def set_superadmin(
    s: requests.Session,
    baseurl: str,
    auth_password: str,
    superadmin: bool,
    user_id: int,
    check_mode: bool = False,
):
    if not check_mode:
        payload = {"p": auth_password}
        new_status = "on" if superadmin else "off"
        r = s.patch(
            baseurl + f"/api/user/{user_id}/super-admin/{new_status}",
            json=payload,
        )
        r.raise_for_status()


def create_user(
    s: requests.Session,
    baseurl: str,
    username: str,
    password: str,
    check_mode: bool = False,
) -> Optional[dict]:
    if not check_mode:
        new_user_payload = {
            "n": username,
            "p": password,
        }
        r = s.put(baseurl + "/api/user", json=new_user_payload)
        r.raise_for_status()

        users = get_users(s, baseurl)
        user = [user for user in users if user["name"] == username][0]
        return user
    return None


def delete_user(
    s: requests.Session, baseurl: str, user_id: int, check_mode: bool = False
):
    if not check_mode:
        payload = {
            "u": [user_id],
        }
        r = s.delete(baseurl + "/api/users", json=payload)
        r.raise_for_status()


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        baseurl=dict(type="str", required=True),
        auth_user=dict(type="str", required=True),
        auth_password=dict(type="str", required=True, no_log=True),
        username=dict(type="str", required=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        password=dict(type="str", required=False, no_log=True),
        superadmin=dict(type="bool", default=False),
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # changed is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    try:
        s = get_authenticated_session(
            module.params["baseurl"],
            module.params["auth_user"],
            module.params["auth_password"],
        )
    except requests.exceptions.RequestException as e:
        module.fail_json(
            msg="Authenticating with testcenter failed",
            status_code=e.response.status_code if e.response else None,
            server_msg=e.response.text if e.response else None,
            exception=e,
            **result,
        )

    existing_users = get_users(s, module.params["baseurl"])
    filtered_users = [
        user for user in existing_users if user["name"] == module.params["username"]
    ]
    user = filtered_users[0] if filtered_users else None

    if module.params["state"] == "present":
        if user:
            if "password" in module.params and module.params["password"]:
                try:
                    password_changed = set_user_password(
                        s,
                        module.params["baseurl"],
                        module.params["username"],
                        module.params["password"],
                        user["id"],
                        module.check_mode,
                    )
                    if password_changed:
                        result["changed"] = True
                except requests.exceptions.RequestException as e:
                    handle_requests_exception(
                        e, module, "Changing user password failed", result
                    )
        else:
            if "password" not in module.params or not module.params["password"]:
                module.fail_json(
                    msg="password arg is required when creating a new user", **result
                )

            try:
                user = create_user(
                    s,
                    module.params["baseurl"],
                    module.params["username"],
                    module.params["password"],
                    module.check_mode,
                )
                result["changed"] = True
            except requests.exceptions.RequestException as e:
                handle_requests_exception(e, module, "Failed to create user", result)

        if user and module.params["superadmin"] != user["isSuperadmin"]:
            try:
                set_superadmin(
                    s,
                    module.params["baseurl"],
                    module.params["auth_password"],
                    module.params["superadmin"],
                    user["id"],
                    module.check_mode,
                )
                result["changed"] = True
            except requests.exceptions.RequestException as e:
                handle_requests_exception(
                    e, module, "Setting superadmin status failed", result
                )

    elif module.params["state"] == "absent" and user:
        try:
            delete_user(s, module.params["baseurl"], user["id"], module.check_mode)
            result["changed"] = True
        except requests.exceptions.RequestException as e:
            handle_requests_exception(e, module, "Deleting user failed", result)

    if user:
        result["user_id"] = user["id"]

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
