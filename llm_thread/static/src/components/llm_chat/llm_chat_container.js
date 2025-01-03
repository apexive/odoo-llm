/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillDestroy, useEffect } from "@odoo/owl";
import { LLMChat } from "./llm_chat";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { useModels } from '@mail/component_hooks/use_models';

export class LLMChatContainer extends Component {
    setup() {
        useModels();
        this.messagingService = useService("messaging");
        this.notification = useService("notification");
        
        this.localChat = undefined;
        this._insertFromProps(this.props);
        
        // Debug setup state
        console.log('LLMChatContainer: Setup', {
            props: this.props,
            localChat: this.localChat
        });

        // Watch for chat updates
        useEffect(
            () => {
                console.log('LLMChatContainer: State Updated', {
                    chat: this.chat,
                    hasThread: Boolean(this.chat?.thread),
                    hasThreadView: Boolean(this.chat?.threadView)
                });
            },
            () => [this.chat, this.chat?.thread, this.chat?.threadView]
        );
        
        onWillDestroy(() => this.deleteLocalChat());
    }

    get chat() {
        const chat = this.props.chat || this.localChat;
        console.log('LLMChatContainer: Get chat', {
            propsChat: this.props.chat,
            localChat: this.localChat,
            returnedChat: chat,
            hasThread: Boolean(chat?.thread),
            hasThreadView: Boolean(chat?.threadView)
        });
        return chat;
    }

    deleteLocalChat() {
        console.log('LLMChatContainer: Deleting local chat', {
            localChat: this.localChat,
            exists: this.localChat?.exists()
        });
        if (this.localChat && this.localChat.exists()) {
            this.localChat.delete();
        }
    }

    async _insertFromProps(props) {
        console.log("LLMChatContainer: Starting _insertFromProps", props);
        const messaging = await this.messagingService.get();
        
        if (!messaging) {
            console.error("LLMChatContainer: Failed to get messaging service");
            return;
        }
        console.log("LLMChatContainer: Got messaging service", messaging);

        if (this.isDestroyed) {
            console.log("LLMChatContainer: Component destroyed before initialization");
            return;
        }

        if (!props.chat && !this.localChat) {
            console.log("LLMChatContainer: Creating new LLMChat with threadId:", props.threadId);
            this.localChat = messaging.models['LLMChat'].insert({ 
                threadId: props.threadId,
            });
            console.log("LLMChatContainer: Created localChat:", this.localChat);
        }

        const chat = props.chat || this.localChat;
        console.log("LLMChatContainer: chat", chat);    
        
        try {
            await chat.loadThread();
            console.log("LLMChatContainer: Thread loaded", {
                chat,
                thread: chat.thread,
                threadView: chat.threadView
            });
        } catch (error) {
            console.error("LLMChatContainer: Error loading thread:", error);
            this.notification.add(error.message || "Failed to load chat", {
                type: 'danger'
            });
        }

        if (this.isDestroyed) {
            this.deleteLocalChat();
        }
    }
}

LLMChatContainer.template = 'llm.ChatContainer';
LLMChatContainer.components = { Dialog, LLMChat };
LLMChatContainer.props = {
    chat: { type: Object, optional: true },
    threadId: { type: Number, optional: true },
    close: { type: Function, optional: true },
};
export class LLMChatDialogAction extends Component {
    setup() {
        this.notification = useService("notification");
        const threadId = this.props.action.params?.thread_id;
        if (!threadId) {
            this.notification.add("No thread ID provided", {
                type: "danger",
                sticky: true,
            });
        }
    }

    get threadId() {
        return this.props.action.params?.thread_id;
    }
}

LLMChatDialogAction.template = 'llm.ChatDialogAction';
LLMChatDialogAction.components = { LLMChatContainer };
LLMChatDialogAction.props = {
    action: Object,
    actionId: { type: [Number, Boolean], optional: true },
};

registry.category("actions").add("llm_chat_dialog", LLMChatDialogAction);