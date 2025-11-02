/** @odoo-module **/

import { attr } from "@mail/model/model_field";
import { registerModel } from "@mail/model/model_core";

registerModel({
  name: "LLMTool",
  fields: {
    id: attr({
      identifying: true,
    }),
    name: attr({
      required: true,
    }),
  },
});
