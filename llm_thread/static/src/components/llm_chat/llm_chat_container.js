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
        const messaging = await this.messagingService.get();
        if (this.isDestroyed) {
            console.log("LLMChatContainer: destroyed");
            return;
        }
        console.log("LLMChatContainer: props", props);
        if (!props.chat && !this.localChat) {
            this.localChat = messaging.models['LLMChat'].insert({ 
                threadId: props.threadId,
            });
        }

        const chat = props.chat || this.localChat;

        console.log("LLMChatContainer: chat", chat);    
        await chat.loadThread();

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