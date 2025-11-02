/** @odoo-module **/

import { one } from "@mail/model/model_field";
import { registerPatch } from "@mail/model/model_core";

registerPatch({
  name: "Messaging",
  fields: {
    llmChat: one("LLMChat", {
      default: {},
      isCausal: true,
    }),
  },
});
