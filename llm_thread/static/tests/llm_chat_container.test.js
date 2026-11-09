// Copyright 2026 Lijo Antony
// License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html).

import { beforeEach, expect, test } from "@odoo/hoot";
import { LLMChatContainer } from "@llm_thread/components/llm_chat_container/llm_chat_container";
import { makeMockEnv } from "@web/../tests/web_test_helpers";
import { mockDate } from "@odoo/hoot-mock";
import { registry } from "@web/core/registry";

const { formatDate } = LLMChatContainer.prototype;

// The labels are translated, so the localization service must have loaded the
// translations before one is read. No other service is needed, and this
// addon's dependency set starts dozens that read the mock server.
beforeEach(async () => {
  const services = registry.category("services");
  for (const [name] of services.getEntries()) {
    if (name !== "localization") {
      services.remove(name);
    }
  }
  await makeMockEnv();
});

// The server sends a thread's write_date as a naive UTC string. Read as local
// time, it aged every thread by the browser's UTC offset: a thread written two
// minutes earlier read "4h ago" in UTC+4. The browser's own zone decides how
// `new Date(string)` parses and hoot cannot mock it, so the Python runner
// (tests/test_chat_container_js.py) opens this suite in a UTC+4 browser.
test("a thread written two minutes ago reads Just now", () => {
  mockDate("2026-10-07 12:41:00");
  expect(String(formatDate("2026-10-07 12:39:00"))).toBe("Just now");
});

test("a thread's age in hours counts from UTC", () => {
  mockDate("2026-10-07 12:41:00");
  expect(String(formatDate("2026-10-07 09:39:00"))).toBe("3h ago");
});
