/** @odoo-module **/

import { clear } from "@mail/model/model_field_command";
import { one } from "@mail/model/model_field";
import { registerPatch } from "@mail/model/model_core";

// 1. Patch MessageActionList to add compute fields for our custom actions
registerPatch({
  name: "MessageActionList",
  fields: {
    actionThumbUp: one("MessageAction", {
      compute() {
        // Show thumb up only for assistant messages using the stored llm_role field
        if (this.message && this.message.llmRole === "assistant") {
          return {};
        }
        return clear();
      },
      inverse: "messageActionListOwnerAsThumbUp",
    }),
    actionThumbDown: one("MessageAction", {
      compute() {
        // Show thumb down only for assistant messages using the stored llm_role field
        if (this.message && this.message.llmRole === "assistant") {
          return {};
        }
        return clear();
      },
      inverse: "messageActionListOwnerAsThumbDown",
    }),
  },
});
