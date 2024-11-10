/** @odoo-module **/

import { Component, useState, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { LLMThreadView } from "../llm_thread_view/llm_thread_view";
import { registry } from "@web/core/registry";

/**
 * Dialog wrapper component for LLM chat
 */
export class LLMChatDialog extends Component {
    setup() {
        // Services
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.actionService = useService("action");

        // State
        this.state = useState({
            isLoading: true,
            hasError: false,
            errorMessage: null,
            thread: null,
        });

        // Load thread data
        this._loadThread();

        // Cleanup on destroy
        onWillDestroy(() => this._cleanup());
    }

    /**
     * Load thread data from server
     * @private
     */
    async _loadThread() {
        try {
            // Get thread data
            const threadData = await this.rpc("/llm/thread/data", {
                thread_id: this.props.threadId,
            });

            if (!threadData) {
                throw new Error(this.env._t("Thread not found"));
            }

            // Create thread view
            this.state.thread = this.env.models.LLMThreadView.insert({
                thread: {
                    id: threadData.id,
                    name: threadData.name,
                    messages: threadData.messages || [],
                    provider: threadData.provider,
                    model: threadData.model,
                },
            });

            this.state.isLoading = false;

        } catch (error) {
            this._handleError(error);
        }
    }

    /**
     * Handle errors
     * @param {Error} error Error object
     * @private
     */
    _handleError(error) {
        this.state.isLoading = false;
        this.state.hasError = true;
        this.state.errorMessage = error.message || this.env._t("Failed to load chat thread");

        this.notification.add(this.state.errorMessage, {
            type: "danger",
            sticky: false,
        });
    }

    /**
     * Cleanup resources
     * @private
     */
    _cleanup() {
        if (this.state.thread) {
            this.state.thread.delete();
        }
    }

    /**
     * Handle retry loading
     * @private
     */
    async _onRetryLoad() {
        this.state.isLoading = true;
        this.state.hasError = false;
        this.state.errorMessage = null;
        await this._loadThread();
    }

    /**
     * Handle thread export
     * @private
     */
    async _onExport() {
        try {
            const action = await this.orm.call(
                'llm.thread',
                'action_export_messages',
                [[this.props.threadId]]
            );
            await this.actionService.doAction(action);
        } catch (error) {
            this.notification.add(
                this.env._t("Failed to export messages"),
                { type: "danger" }
            );
        }
    }

    /**
     * Handle thread clearing
     * @private
     */
    async _onClear() {
        this.dialog.add(ConfirmDialog, {
            title: this.env._t("Clear Chat"),
            body: this.env._t("Are you sure you want to clear all messages? This cannot be undone."),
            confirm: async () => {
                try {
                    await this.orm.call(
                        'llm.thread',
                        'action_clear_messages',
                        [[this.props.threadId]]
                    );
                    await this._loadThread();
                } catch (error) {
                    this.notification.add(
                        this.env._t("Failed to clear messages"),
                        { type: "danger" }
                    );
                }
            },
        });
    }
}

LLMChatDialog.template = "llm.ChatDialog";
LLMChatDialog.components = {
    Dialog,
    LLMThreadView,
};

LLMChatDialog.props = {
    threadId: {
        type: Number,
        required: true,
    },
    close: {
        type: Function,
        required: true,
    },
};

/**
 * Chat dialog action component
 */
export class LLMChatDialogAction extends Component {
    setup() {
        this.title = this.env.config.actionTitle || this.env._t("Chat");
        this.threadId = this.props.params?.thread_id;

        if (!this.threadId) {
            this.notification.add(
                this.env._t("No thread specified"),
                { type: "danger" }
            );
            if (this.props.close) {
                this.props.close();
            }
        }
    }

    /**
     * Handle dialog close
     */
    onClose() {
        if (this.props.close) {
            this.props.close();
        }
    }
}

LLMChatDialogAction.template = "llm.ChatDialogAction";
LLMChatDialogAction.components = {
    Dialog,
    LLMChatDialog,
};

// Register components and action
registry.category("components").add("LLMChatDialog", LLMChatDialog);
registry.category("actions").add("llm_chat_dialog", LLMChatDialogAction);
