/** @odoo-module **/

import { registry } from "@web/core/registry";
import { LLMChatContainer } from "./llm_chat_container";

export class LLMChatDialogAction extends LLMChatContainer {
    setup() {
        super.setup();
        const threadId = this.props.action.params?.thread_id;
        if (!threadId) {
            this.env.services.notification.add(
                this.env._t("No thread ID provided"),
                { type: "danger", sticky: true }
            );
        }
    }

    get threadId() {
        return this.props.action.params?.thread_id;
    }
}

LLMChatDialogAction.template = 'llm.ChatDialogAction';
registry.category("actions").add("llm_chat_dialog", LLMChatDialogAction);