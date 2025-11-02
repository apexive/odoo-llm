/** @odoo-module **/

import { attr, many, one } from "@mail/model/model_field";
import { registerModel } from "@mail/model/model_core";

registerModel({
  name: "LLMModel",
  fields: {
    id: attr({
      identifying: true,
    }),
    name: attr({
      required: true,
    }),
    llmProvider: one("LLMProvider", {
      inverse: "llmModels",
    }),
    threads: many("Thread", {
      inverse: "llmModel",
    }),
    default: attr({
      default: false,
    }),
  },
});
