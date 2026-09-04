import json
from unittest.mock import MagicMock

import requests
from requests import Response

from ansible_collections.kompetenztestde.testcenter.plugins.modules import (
    testcenter_app_config,
)

SYSTEM_CONFIG_RESPONSE = b"""{
    "version": "18.2.0",
    "customTexts": { },
    "appConfig": {
        "legalNoticeHtml": "<p>Lorem ipsum dolor sit amet</p>"
    },
    "broadcastingServiceUri": "http://blabla",
    "fileServiceUri": "http://blabla",
    "veronaPlayerApiVersionMin": 2,
    "veronaPlayerApiVersionMax": 4,
    "baseUrl": "http://testcenter.de",
    "supportedBrowsers": [
        "chrome 131",
        "firefox 133"
    ],
    "passwordMinLength": 7,
    "passwordPattern": "^\\\\d+$"
}"""


def test_get_config_not_empty():
    response = Response()
    response.status_code = 200
    response._content = SYSTEM_CONFIG_RESPONSE
    response.encoding = "utf-8"

    session = requests.Session()
    session.get = MagicMock(return_value=response)

    config = testcenter_app_config.get_config(session, "https://tc.example.com")

    assert config == {"legalNoticeHtml": "<p>Lorem ipsum dolor sit amet</p>"}
    session.get.assert_called_once_with(
        "https://tc.example.com/api/system/config",
    )


def test_get_config_empty():
    response = Response()
    response.status_code = 200
    response._content = b""
    response.encoding = "utf-8"

    session = requests.Session()
    session.get = MagicMock(return_value=response)

    config = testcenter_app_config.get_config(session, "https://tc.example.com")

    assert config == {}
    session.get.assert_called_once_with(
        "https://tc.example.com/api/system/config",
    )
