# Copyright 2026 Lijo Antony
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

from unittest import mock

from odoo.tests import HttpCase, tagged
from odoo.tests.common import ChromeBrowser

from odoo.addons.web.tests.test_js import unit_test_error_checker

# Hoot names a suite after the test module path, with "../tests/" stripped.
# See web/static/tests/_framework/module_set.hoot.js:getSuitePath.
SUITE_PATH = "@llm_thread/llm_chat_container"

# A zone away from UTC. odoo-bin sets TZ=UTC for the whole process, so the test
# browser inherits UTC, and there a naive UTC string read as local time is
# still right: the suite could not fail for the defect it guards against.
BROWSER_TIME_ZONE = "Etc/GMT-4"


def _hoot_job_hash(descriptor):
    """Reproduce the hoot job id hash used by the /web/tests "id" filter."""
    value = 0
    for char in descriptor:
        value = ((value << 5) - value + ord(char)) & 0xFFFFFFFF
    return f"{value:08x}"


@tagged("post_install", "-at_install")
class TestChatContainerSuite(HttpCase):
    """Run the chat container's hoot suite in a browser away from UTC."""

    def test_unit_chat_container(self):
        navigate_to = ChromeBrowser.navigate_to

        def navigate_away_from_utc(browser, url, wait_stop=False):
            browser._websocket_request(
                "Emulation.setTimezoneOverride",
                params={"timezoneId": BROWSER_TIME_ZONE},
            )
            return navigate_to(browser, url, wait_stop=wait_stop)

        with mock.patch.object(ChromeBrowser, "navigate_to", navigate_away_from_utc):
            self.browser_js(
                "/web/tests?headless&loglevel=2&preset=desktop&timeout=15000"
                f"&id={_hoot_job_hash(SUITE_PATH)}",
                "",
                "",
                login="admin",
                timeout=180,
                success_signal="[HOOT] Test suite succeeded",
                error_checker=unit_test_error_checker,
            )
