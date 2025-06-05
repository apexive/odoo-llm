/** @odoo-module **/

import {one} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "Thread",
    fields: {
        prompt_id: one("LLMPrompt", {
            inverse: "threads",
        }),
    },
});
