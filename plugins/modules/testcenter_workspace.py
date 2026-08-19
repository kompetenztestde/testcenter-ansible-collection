#!/usr/bin/python

from __future__ import absolute_import, division, print_function
import os
from typing import Optional, List

import requests

__metaclass__ = type

DOCUMENTATION = r"""
---
module: testcenter_workspace

short_description: Manage IQB Testcenter workspaces

version_added: "1.0.0"

description: Add, edit or remove IQB Testcenter workspaces

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
    name:
        description: Name of the workspace
        required: true
        type: str
    state:
        description: State of the user
        default: present
        choices:
            - present
            - absent
    keep_existing:
        description: Don't delete existing files
        default: true
        type: bool
    users:
        description: Users with access permission for the workspace
        type: list
        elements: dict
        options:
            name:
                description: Name of the user
                type: str
                required: true
            role:
                description: Access role of the user
                type: str
                choices:
                    - RW
                    - MO
                    - RO
                default: RW
    files:
        description: Filenames of local files that should get uploaded to the workspace
        type: list
        elements: str

author:
    - Oskar Jauch (oskar.jauch@uni-jena.de)
"""

EXAMPLES = r"""
# create a new workspace
- name: Create new user
  kompetenztestde.testcenter.testcenter_user:
    baseurl: https://example.com
    auth_user: super
    auth_password: super123
    name: Example Workspace
    state: present

# delete an existing workspace
- name: Delete an existing workspace
  kompetenztestde.testcenter.testcenter_user:
    baseurl: https://example.com
    auth_user: super
    auth_password: super123
    name: Example Workspace
    state: absent
"""

RETURN = r"""
# These are examples of possible return values, and in general should use other names for return values.
workspace_id:
    description: ID of the workspace created, edited or removed
    type: int
    sample: 1
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.kompetenztestde.testcenter.plugins.module_utils.testcenter import (
    get_authenticated_session,
    handle_requests_exception,
    get_users,
    get_user_id,
)


def get_workspaces(s: requests.Session, baseurl: str) -> List[dict]:
    r = s.get(baseurl + "/api/workspaces")
    r.raise_for_status()
    return r.json()


def create_workspace(
    s: requests.Session, baseurl: str, name: str, check_mode: bool = False
) -> Optional[dict]:
    if not check_mode:
        payload = {
            "name": name,
        }
        r = s.put(baseurl + "/api/workspace", json=payload)
        r.raise_for_status()

        workspaces = get_workspaces(s, baseurl)
        filtered_workspaces = [
            workspace for workspace in workspaces if workspace["name"] == name
        ]
        return filtered_workspaces[0]
    return None


def delete_workspace(
    s: requests.Session, baseurl: str, workspace_id: int, check_mode: bool = False
):
    if not check_mode:
        payload = {"ws": [workspace_id]}
        r = s.delete(baseurl + "/api/workspaces", json=payload)
        r.raise_for_status()


def get_workspace_users(
    s: requests.Session, baseurl: str, workspace_id: int
) -> List[dict]:
    r = s.get(baseurl + f"/api/workspace/{workspace_id}/users")
    r.raise_for_status()
    return r.json()


def set_workspace_permissions(
    s: requests.Session,
    baseurl: str,
    workspace_id: int,
    users: List[dict],
    check_mode: bool = False,
):
    if not check_mode:
        payload = {"u": users}
        r = s.patch(f"{baseurl}/api/workspace/{workspace_id}/users", json=payload)
        r.raise_for_status()


def get_workspace_files(s: requests.Session, baseurl: str, workspace_id: int) -> dict:
    r = s.get(f"{baseurl}/api/workspace/{workspace_id}/files")
    r.raise_for_status()
    files = r.json()
    if type(files) is list and not files:
        return {}
    return files


def delete_workspace_files(
    s: requests.Session, baseurl: str, workspace_id: int, files_to_delete: List[str]
) -> dict:
    payload = {"f": files_to_delete}
    r = s.delete(f"{baseurl}/api/workspace/{workspace_id}/files", json=payload)
    r.raise_for_status()
    return r.json()


def upload_workspace_file(
    s: requests.Session, baseurl: str, workspace_id: int, file: dict
) -> dict:
    files = {"fileforvo": open(file["path"], "rb")}
    r = s.post(f"{baseurl}/api/workspace/{workspace_id}/file", files=files)
    r.raise_for_status()
    return r.json()


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        baseurl=dict(type="str", required=True),
        auth_user=dict(type="str", required=True),
        auth_password=dict(type="str", required=True, no_log=True),
        name=dict(type="str", required=True),
        state=dict(type="str", choices=["present", "absent"], default="present"),
        users=dict(
            type="list",
            elements="dict",
            options=dict(
                name=dict(type="str", required=True),
                role=dict(type="str", choices=["RW", "MO", "RO"], default="RW"),
            ),
        ),
        files=dict(type="list", elements="str"),
        keep_existing=dict(type="bool", default=True),
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
        handle_requests_exception(
            e, module, "Authenticating with testcenter failed", result
        )

    try:
        existing_workspaces = get_workspaces(s, module.params["baseurl"])
    except requests.exceptions.RequestException as e:
        handle_requests_exception(e, module, "Failed getting workspaces", result)

    filtered_workspaces = [
        workspace
        for workspace in existing_workspaces
        if workspace["name"] == module.params["name"]
    ]
    workspace = filtered_workspaces[0] if filtered_workspaces else None

    if module.params["state"] == "present" and not workspace:
        try:
            workspace = create_workspace(
                s, module.params["baseurl"], module.params["name"], module.check_mode
            )
            result["changed"] = True
        except requests.exceptions.RequestException as e:
            handle_requests_exception(e, module, "Failed to create workspace", result)
    elif module.params["state"] == "absent" and workspace:
        try:
            delete_workspace(
                s, module.params["baseurl"], workspace["id"], module.check_mode
            )
            result["changed"] = True
        except requests.exceptions.RequestException as e:
            handle_requests_exception(e, module, "Failed to delete workspace", result)

    # configure user access permissions
    if (
        module.params["state"] == "present"
        and workspace
        and "users" in module.params
        and module.params["users"]
    ):
        try:
            users = get_users(s, module.params["baseurl"])
        except requests.exceptions.RequestException as e:
            handle_requests_exception(e, module, "Failed getting users", result)

        # compare existing permissions
        try:
            existing_users = get_workspace_users(
                s, module.params["baseurl"], workspace["id"]
            )
        except requests.exceptions.RequestException as e:
            handle_requests_exception(
                e, module, "Failed getting workspace users", result
            )

        # filter users without role
        existing_users = [user for user in existing_users if user["role"]]

        wanted_users = [
            {"id": get_user_id(users, user["name"]), "role": user["role"]}
            for user in module.params["users"]
        ]

        permissions_changed = False
        for existing_user in existing_users:
            if not [
                wanted_user
                for wanted_user in wanted_users
                if wanted_user["id"] == existing_user["id"]
                and wanted_user["role"] == existing_user["role"]
            ]:
                permissions_changed = True
                break

        if not permissions_changed:
            for wanted_user in wanted_users:
                if not [
                    existing_user
                    for existing_user in existing_users
                    if existing_user["id"] == wanted_user["id"]
                    and existing_user["role"] == wanted_user["role"]
                ]:
                    permissions_changed = True
                    break

        if permissions_changed:
            set_workspace_permissions(
                s,
                module.params["baseurl"],
                workspace["id"],
                wanted_users,
                module.check_mode,
            )
            result["changed"] = True

    # handle file configuration
    if (
        module.params["state"] == "present"
        and workspace
        and "files" in module.params
        and module.params["files"]
    ):
        try:
            existing_files = get_workspace_files(
                s, module.params["baseurl"], workspace["id"]
            )
        except requests.exceptions.RequestException as e:
            handle_requests_exception(
                e, module, "Failed to get workspace files", result
            )

        # module.fail_json(msg="debug", cwd=os.getcwd(), **result)

        all_files = []
        for filetype, files in existing_files.items():
            for file in files:
                all_files.append({**file, "filetype": filetype})

        wanted_files = []
        for filepath in module.params["files"]:
            try:
                size = os.path.getsize(filepath)
                modification_time = os.path.getmtime(filepath)
            except OSError as e:
                module.fail_json(
                    f"Failed to get metadata for file {filepath}",
                    file=filepath,
                    **result,
                )
            wanted_file = {
                "name": os.path.split(filepath)[1],
                "size": size,
                "modification_time": modification_time,
                "path": filepath,
            }
            wanted_files.append(wanted_file)

        files_to_add = []
        files_to_delete = []

        for existing_file in all_files:
            if not [
                wanted_file
                for wanted_file in wanted_files
                if existing_file["name"] == wanted_file["name"]
            ]:
                files_to_delete.append(existing_file)

        for wanted_file in wanted_files:
            if not [
                existing_file
                for existing_file in all_files
                if existing_file["name"] == wanted_file["name"]
                and existing_file["size"] == wanted_file["size"]
                and existing_file["modificationTime"]
                >= wanted_file["modification_time"]
            ]:
                files_to_add.append(wanted_file)

        if files_to_delete and not module.params["keep_existing"]:
            result["changed"] = True

            if not module.check_mode:
                files_to_delete = [
                    f"{file['filetype']}/{file['name']}" for file in files_to_delete
                ]
                try:
                    delete_workspace_files(
                        s, module.params["baseurl"], workspace["id"], files_to_delete
                    )
                except requests.exceptions.RequestException as e:
                    handle_requests_exception(
                        e, module, "Failed to delete files", result
                    )

        if files_to_add:
            result["changed"] = True

            if not module.check_mode:
                for file in files_to_add:
                    try:
                        upload_workspace_file(
                            s, module.params["baseurl"], workspace["id"], file
                        )
                    except requests.exceptions.RequestException as e:
                        handle_requests_exception(
                            e, module, f"Failed to upload file {file['name']}", result
                        )

    if workspace:
        result["workspace_id"] = workspace["id"]

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
