/** @odoo-module **/

import { attr, many } from "@mail/model/model_field";
import { registerModel } from "@mail/model/model_core";

registerModel({
  name: "LLMProvider",
  fields: {
    id: attr({
      identifying: true,
    }),
    name: attr({
      required: true,
    }),
    llmModels: many("LLMModel", {
      inverse: "llmProvider",
    }),
  },
});
