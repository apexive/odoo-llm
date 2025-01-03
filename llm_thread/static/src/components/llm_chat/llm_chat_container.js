/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillDestroy } from "@odoo/owl";
import { LLMChat } from "./llm_chat";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { useModels } from '@mail/component_hooks/use_models';

export class LLMChatContainer extends Component {
    setup() {
        useModels();
        this.messagingService = useService("messaging");
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        
        this.localChat = undefined;
        this._insertFromProps(this.props);
        onWillDestroy(() => this.deleteLocalChat());
    }

    get chat() {
        return this.props.chat || this.localChat;
    }

    deleteLocalChat() {
        if (this.localChat && this.localChat.exists()) {
            this.localChat.delete();
        }
    }

    async _insertFromProps(props) {
        try {
            const messaging = await this.messagingService.get();
            if (this.isDestroyed) {
                return;
            }
            
            const values = { 
                threadId: props.threadId,
                env: this.env
            };
            
            const hasToCreateChat = !props.chat && !this.localChat;
            
            if (hasToCreateChat) {
                this.localChat = messaging.models['LLMChat'].insert(values);
            }

            const chat = props.chat || this.localChat;
            
            if (!hasToCreateChat) {
                chat.update(values);
            }
            
            if (this.isDestroyed) {
                this.deleteLocalChat();
                return;
            }

            await chat.loadThread();
        } catch (error) {
            console.error('Error in _insertFromProps:', error);
            this.notification.add('Failed to load chat thread', {
                type: 'danger',
                details: error.toString()
            });
        }
    }
}

LLMChatContainer.template = 'llm.ChatContainer';
LLMChatContainer.components = { 
    Dialog,
    LLMChat,
};
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
LLMChatDialogAction.components = {
    LLMChatContainer,
};
LLMChatDialogAction.props = {
    action: Object,
    actionId: { type: [Number, Boolean], optional: true },
};
registry.category("actions").add("llm_chat_dialog", LLMChatDialogAction);