/** @odoo-module **/

import { one } from "@mail/model/model_field";
import { registerPatch } from "@mail/model/model_core";

// 2. Patch MessageAction for correct owner computation and sequence
registerPatch({
  name: "MessageAction",
  fields: {
    // === New fields (inverse relations) ===
    messageActionListOwnerAsThumbUp: one("MessageActionList", {
      identifying: true,
      inverse: "actionThumbUp",
    }),
    messageActionListOwnerAsThumbDown: one("MessageActionList", {
      identifying: true,
      inverse: "actionThumbDown",
    }),

    // === Patched fields ===

    messageActionListOwner: {
      compute() {
        // Check our custom inverse relations first
        if (this.messageActionListOwnerAsThumbUp) {
          return this.messageActionListOwnerAsThumbUp;
        }
        if (this.messageActionListOwnerAsThumbDown) {
          return this.messageActionListOwnerAsThumbDown;
        }
        // If not our actions, call the original compute logic
        return this._super();
      },
    },

    sequence: {
      compute() {
        if (this.messageActionListOwnerAsThumbUp) {
          return 15;
        }
        if (this.messageActionListOwnerAsThumbDown) {
          return 16;
        }
        return this._super();
      },
    },
  },
});
