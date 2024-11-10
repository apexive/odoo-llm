/** @odoo-module **/

import { Component, useState, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { LLMThreadView } from "../llm_thread_view/llm_thread_view";

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

            this.state.thread = threadData;
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
        // Add cleanup if needed
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
        const dialog = this.dialog;
        return new Promise((resolve) => {
            dialog.add(Dialog, {
                title: this.env._t("Clear Chat"),
                body: this.env._t("Are you sure you want to clear all messages? This cannot be undone."),
                confirmLabel: this.env._t("Clear"),
                cancelLabel: this.env._t("Cancel"),
                technical: false,
                size: 'md',
                onClose: () => resolve(false),
                buttons: [
                    {
                        text: this.env._t("Cancel"),
                        click: () => resolve(false),
                        close: true,
                    },
                    {
                        text: this.env._t("Clear"),
                        classes: 'btn-danger',
                        click: async () => {
                            try {
                                await this.orm.call(
                                    'llm.thread',
                                    'action_clear_messages',
                                    [[this.props.threadId]]
                                );
                                await this._loadThread();
                                resolve(true);
                            } catch (error) {
                                this.notification.add(
                                    this.env._t("Failed to clear messages"),
                                    { type: "danger" }
                                );
                                resolve(false);
                            }
                        },
                        close: true,
                    },
                ],
            });
        });
    }
}

LLMChatDialog.template = "llm.ChatDialog";
LLMChatDialog.components = {
    Dialog,
    LLMThreadView,
};

LLMChatDialog.props = {
    threadId: { type: Number, required: true },
    close: { type: Function, optional: true },
};

/**
 * Client action component for the chat dialog
 */
class LLMChatDialogClientAction extends Component {
    setup() {
        this.notification = useService("notification");
        this.actionService = useService("action");
    }

    /**
     * @returns {string} Dialog title
     */
    get title() {
        return this.props.action.name || this.env._t("Chat");
    }

    /**
     * @returns {number|undefined} Thread ID from action params
     */
    get threadId() {
        return this.props.action.params?.thread_id;
    }
}

LLMChatDialogClientAction.template = 'llm.ChatDialogAction';
LLMChatDialogClientAction.components = {
    Dialog,
    LLMChatDialog,
};

// Props for client action
LLMChatDialogClientAction.props = {
    action: Object,
    actionId: { type: [Number, Boolean], optional: true },
};

// Register the client action
registry.category("actions").add("llm_chat_dialog", LLMChatDialogClientAction);

export { LLMChatDialogClientAction };
