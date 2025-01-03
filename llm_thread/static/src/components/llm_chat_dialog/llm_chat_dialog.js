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
            threadView: null,
        });

        this._loadThread();
    }

    async _loadThread() {
        try {
            this.state.isLoading = true;
            this.state.hasError = false;

            // Fetch thread data
            const threadData = await this.rpc('/llm/thread/data', {
                thread_id: this.props.threadId
            });

            // Create thread structure
            const thread = {
                id: this.props.threadId,
                model: 'llm.thread',
                name: threadData.name,
                isTemporary: false,
                channel: null,
                hasCallFeature: false,
                message_ids: threadData.messages.map(msg => ({
                    id: msg.id,
                    body: msg.content,
                    author: { id: msg.author_id, name: msg.author },
                    date: msg.timestamp,
                    message_type: 'comment',
                    llm_role: msg.role,
                })),
            };

            // Create threadCache
            const threadCache = {
                id: `cache_${this.props.threadId}`,
                thread,
                isLoaded: true,
                hasLoadingFailed: false,
                messages: thread.message_ids,
            };

            // Create messageListView
            const messageListView = {
                thread,
                threadCache,
                messages: threadCache.messages,
                components: { ThreadView },
            };

            // Create composerView
            const composerView = {
                thread,
                isDisabled: false,
                onInput: this._onComposerInput.bind(this),
                onSend: this._onSendMessage.bind(this),
            };

            // Create threadView structure
            this.state.threadView = {
                thread,
                threadCache,
                messageListView,
                composerView,
                threadViewer: { chatWindow: false },
                isLoading: false,
                extraClass: 'o_LLMThread',
            };

            this.state.isLoading = false;
        } catch (error) {
            console.error('Chat loading error:', error);
            this.state.hasError = true;
            this.state.errorMessage = error.message || "Failed to load chat thread";
            this.state.isLoading = false;
        }
    }

    _onComposerInput(value) {
        if (this.state.threadView?.composerView) {
            this.state.threadView.composerView.textInputContent = value;
        }
    }

    async _onSendMessage(content) {
        if (!content.trim()) return;

        try {
            // Post user message
            const message = await this.rpc('/llm/thread/post_message', {
                thread_id: this.props.threadId,
                content: content,
            });

            // Add message to threadCache
            this.state.threadView.threadCache.messages.push(message);

            // Start streaming response
            const eventSource = new EventSource(
                `/llm/thread/stream_response?thread_id=${this.props.threadId}`,
                { withCredentials: true }
            );

            let assistantMessage = '';

            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'content' && data.content) {
                    assistantMessage += data.content;
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
        const messages = this.state.threadView.threadCache.messages;
        const lastMessage = messages[messages.length - 1];
        
        if (lastMessage && lastMessage.llm_role === 'assistant') {
            lastMessage.body = content;
        } else {
            messages.push({
                id: `temp_${Date.now()}`,
                llm_role: 'assistant',
                body: content,
                author: { id: -1, name: 'Assistant' },
                date: new Date().toISOString(),
            });
        }

        // Force update
        this.state.threadView = { ...this.state.threadView };
    }
}

LLMChatDialog.template = "llm.ChatDialog";
LLMChatDialog.components = { 
    Dialog,
    ThreadView
};

LLMChatDialog.props = {
    threadId: { type: Number, required: true },
    close: { type: Function, optional: true },
    title: { type: String, optional: true },
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