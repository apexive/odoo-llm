/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { ThreadView } from "@mail/components/thread_view/thread_view";
import { registry } from "@web/core/registry";

export class LLMChatDialog extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.messaging = useService("messaging");

        this.state = useState({
            isLoading: true,
            hasError: false,
            errorMessage: null,
            threadViewer: null,
        });

        this._loadThread();
    }

    async _loadThread() {
        try {
            const messaging = await this.messaging.get();
            
            const thread = messaging.models['mail.thread'].insert({
                id: this.props.threadId,
                model: 'llm.thread'
            });

            const threadViewer = messaging.models['ThreadViewer'].insert({
                thread,
                extraClass: 'o_LLMThread'
            });

            this.state.threadViewer = threadViewer;
        } catch (error) {
            this.state.hasError = true;
            this.state.errorMessage = error.message || "Failed to load chat thread";
        } finally {
            this.state.isLoading = false;
        }
    }
}

LLMChatDialog.template = "llm.ChatDialog";
LLMChatDialog.components = { 
    Dialog, 
    ThreadView,
};

LLMChatDialog.props = {
    threadId: { type: Number, required: true },
    close: { type: Function, optional: true },
};

export class LLMChatDialogAction extends Component {
    setup() {
        this.notification = useService("notification");
        this.actionService = useService("action");

        const threadId = this.props.action.params?.thread_id;
        if (!threadId) {
            this.notification.add(this.env._t("No thread ID provided"), {
                type: "danger",
                sticky: true,
            });
        }
    }

    get title() {
        return this.props.action.name || this.env._t("Chat");
    }

    get threadId() {
        return this.props.action.params?.thread_id;
    }
}

LLMChatDialogAction.template = "llm.ChatDialogAction";
LLMChatDialogAction.components = {
    LLMChatDialog,
};

LLMChatDialogAction.props = {
    action: Object,
    actionId: { type: [Number, Boolean], optional: true },
};

// Register the client action
registry.category("actions").add("llm_chat_dialog", LLMChatDialogAction);