#!/usr/bin/python

from __future__ import absolute_import, division, print_function
from typing import Optional

import requests

__metaclass__ = type

DOCUMENTATION = r"""
---
module: testcenter_app_config

short_description: Manage IQB Testcenter App Config

version_added: "1.0.0"

description: Manage IQB Testcenter App Config such as text replacements or imprint

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
    config:
        description: Configuration that should get set
        required: true
        type: dict

author:
    - Oskar Jauch (oskar.jauch@uni-jena.de)
"""

EXAMPLES = r"""
# update app config
- name: Update app config
  kompetenztestde.testcenter.testcenter_app_config:
    baseurl: https://example.com
    auth_user: super
    auth_password: super123
    config:
      key: value
      key2: value2
"""

RETURN = r"""
config:
    description: current config of the testcenter instance
    type: dict
    sample: {}
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.kompetenztestde.testcenter.plugins.module_utils.testcenter import (
    get_authenticated_session,
    handle_requests_exception,
    get_users,
)


def get_config(session, baseurl):
    r = session.get(baseurl + '/api/system/config')
    return r.json()['appConfig'] if r.text else {}


def update_config(session, baseurl, updated_config):
    r = session.patch(baseurl + '/api/system/config/app', json=updated_config)
    return r.json() if r.text else {}


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        baseurl=dict(type="str", required=True),
        auth_user=dict(type="str", required=True),
        auth_password=dict(type="str", required=True, no_log=True),
        config=dict(type="dict", required=True),
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

    current_config = get_config(s, module.params["baseurl"])
    result["config"] = current_config

    # check if config is already up to date
    to_update = {}
    for key, value in module.params["config"].items():
        if key not in current_config or current_config[key] != value:
            to_update[key] = value
            result["changed"] = True

    if to_update and not module.check_mode:
        updated_config = update_config(s, module.params["baseurl"], to_update)
        result["config"] = updated_config

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
