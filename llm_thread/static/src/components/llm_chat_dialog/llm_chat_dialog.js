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
        this.orm = useService("orm");

        this.state = useState({
            isLoading: true,
            hasError: false,
            errorMessage: null,
            threadViewer: null,
            threadData: null,
        });

        this._loadThread();
    }

    async _loadThread() {
        try {
            this.state.isLoading = true;
            this.state.hasError = false;

            // First fetch thread data
            this.state.threadData = await this.rpc('/llm/thread/data', {
                thread_id: this.props.threadId
            });

            // Then initialize messaging
            const messaging = await this.messaging.get();
            
            if (!messaging || !messaging.models) {
                throw new Error("Messaging system not initialized");
            }

            // Create thread in the messaging store
            const thread = messaging.models['Thread'].insert({
                id: this.props.threadId,
                model: 'llm.thread',
                name: this.state.threadData.name,
                message_ids: this.state.threadData.messages.map(msg => ({
                    id: msg.id,
                    body: msg.content,
                    author: { id: messaging.currentPartner.id, name: msg.author },
                    llm_role: msg.role,
                    date: msg.timestamp,
                })),
            });

            // Create thread viewer
            const threadViewer = messaging.models['ThreadViewer'].insert({
                thread,
                hasThreadView: true,
                threadView: {
                    messageListPosition: 'bottom',
                    hasScrollAdjust: true,
                },
            });

            this.state.threadViewer = threadViewer;
            this.state.isLoading = false;
        } catch (error) {
            console.error('Chat loading error:', error);
            this.state.hasError = true;
            this.state.errorMessage = error.message || "Failed to load chat thread";
            this.state.isLoading = false;
        }
    }

    async _sendMessage(content) {
        try {
            // Post message to backend
            const message = await this.rpc('/llm/thread/post_message', {
                thread_id: this.props.threadId,
                content: content,
            });

            // Create SSE connection for streaming response
            const eventSource = new EventSource(
                `/llm/thread/stream_response?thread_id=${this.props.threadId}`,
                { withCredentials: true }
            );

            let assistantMessage = '';

            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'content' && data.content) {
                    assistantMessage += data.content;
                    // Update UI with partial response
                    this._updateAssistantMessage(assistantMessage);
                }
                
                if (data.type === 'end') {
                    eventSource.close();
                }

                if (data.type === 'error') {
                    this.notification.add(data.error, {
                        type: 'danger',
                    });
                    eventSource.close();
                }
            };

            eventSource.onerror = () => {
                eventSource.close();
                this.notification.add(this.env._t("Error receiving AI response"), {
                    type: 'danger',
                });
            };
        } catch (error) {
            this.notification.add(this.env._t("Failed to send message"), {
                type: 'danger',
            });
            console.error('Message sending error:', error);
        }
    }

    _updateAssistantMessage(content) {
        if (!this.state.threadViewer?.thread) return;

        const messaging = this.messaging.get();
        if (!messaging) return;

        // Update or create assistant message
        const lastMessage = this.state.threadViewer.thread.messages[this.state.threadViewer.thread.messages.length - 1];
        
        if (lastMessage && lastMessage.llm_role === 'assistant') {
            lastMessage.update({ body: content });
        } else {
            messaging.models['Message'].insert({
                id: `temp_${Date.now()}`,
                author: { id: messaging.currentPartner.id, name: 'Assistant' },
                body: content,
                llm_role: 'assistant',
                thread: this.state.threadViewer.thread,
            });
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