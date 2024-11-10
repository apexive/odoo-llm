/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillDestroy } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { ThreadViewModel } from "../models";
import { LLMThreadView } from "../llm_thread_view/llm_thread_view";
import { ErrorBoundary } from "@web/core/errors/error_boundary";

export class LLMChatDialog extends Component {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.messageBus = useService("messaging_service");

        this.threadData = null;
        this.threadView = null;
        this._isDestroyed = false;

        // Subscribe to events
        this.messageBus.addEventListener('message-retry', this._onMessageRetry.bind(this));

        // Cleanup on destroy
        onWillDestroy(() => {
            this._isDestroyed = true;
            if (this.threadView) {
                this.threadView.cleanup();
            }
            this.messageBus.removeEventListener('message-retry', this._onMessageRetry);
        });

        this._loadThread();
    }

    async _loadThread() {
        try {
            this.threadData = await this.rpc("/llm/thread/data", {
                thread_id: this.props.threadId,
            });

            if (this._isDestroyed) return;

            this.threadView = new ThreadViewModel(this.env, {
                thread: {
                    id: this.threadData.id,
                    name: this.threadData.name,
                    messages: this.threadData.messages,
                    provider: this.threadData.provider,
                    model: this.threadData.model
                },
                hasLoadedMessages: true,
            });
        } catch (error) {
            if (this._isDestroyed) return;

            this.notification.notify({
                title: "Error",
                message: error.message || "Failed to load chat thread",
                type: "danger"
            });
        }
    }

    async _onMessageRetry({ detail: { messageId } }) {
        if (!this.threadView) return;

        try {
            await this.threadView.retryMessage(messageId);
        } catch (error) {
            this.notification.notify({
                title: "Error",
                message: error.message || "Failed to retry message",
                type: "danger"
            });
        }
    }
}

LLMChatDialog.components = {
    Dialog,
    LLMThreadView,
    ErrorBoundary
};

LLMChatDialog.props = {
    threadId: Number,
    close: Function,
};

LLMChatDialog.template = "llm.ChatDialog";

// Client Action Component
export class LLMChatDialogAction extends Component {
    setup() {
        this.title = this.env.config.actionTitle || "Chat";
        this.threadId = this.props.params?.thread_id;
    }

    onClose() {
        if (this.props.close) {
            this.props.close();
        }
    }
}

LLMChatDialogAction.components = {
    Dialog,
    LLMChatDialog,
};

LLMChatDialogAction.template = "llm.ChatDialogAction";

// Register the client action
registry.category("actions").add("llm_chat_dialog", {
    component: LLMChatDialogAction,
});
