/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

/**
 * Client action handler for opening AI chat in chatter.
 *
 * This replaces the unreliable bus notification pattern.
 * When "Process with AI" button is clicked:
 * 1. Backend creates thread, returns this client action
 * 2. This action stores pending state in llm.store service
 * 3. Navigates to record form view
 * 4. Chatter picks up pending state on mount and opens AI chat
 */
registry.category("actions").add("llm_open_chatter", async (env, action) => {
  const { thread_id, model, res_id } = action.params || {};

  if (!thread_id || !model || !res_id) {
    console.error("[llm_open_chatter] Missing required params:", action.params);
    env.services.notification.add(
      _t("Could not open AI chat. Required information is missing."),
      {
        type: "danger",
      }
    );
    return;
  }

  // Store pending open in llm.store service
  const llmStore = env.services["llm.store"];
  if (!llmStore) {
    console.error("[llm_open_chatter] llm.store service not found");
    env.services.notification.add(
      _t("AI chat is not available. Please refresh the page and try again."),
      {
        type: "danger",
      }
    );
    return;
  }

  llmStore.setPendingOpenInChatter({
    threadId: thread_id,
    model: model,
    resId: res_id,
    autoGenerate: true, // Auto-trigger AI generation with prepended messages
  });

  // Navigate to the record's form view
  // Chatter will pick up the pending state on mount
  return env.services.action.doAction({
    type: "ir.actions.act_window",
    res_model: model,
    res_id: res_id,
    views: [[false, "form"]],
    target: "current",
  });
});
