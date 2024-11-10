/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

class LLMChatDialog extends Dialog {
    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.threadData = null;
        this._loadThread();
    }

    async _loadThread() {
        const threadId = this.props.params.thread_id;
        this.threadData = await this.rpc("/llm/thread/data", {
            thread_id: threadId,
        });

        this.threadView = {
            thread: {
                id: this.threadData.id,
                name: this.threadData.name,
                messages: this.threadData.messages,
                isLoading: false,
                async loadMessages() {
                    // Messages are pre-loaded in this case
                    return true;
                },
                async postMessage(message) {
                    return await this.rpc("/llm/thread/post_message", {
                        thread_id: this.threadData.id,
                        content: message.content,
                        role: message.role,
                    });
                },
                async getAIResponse(content) {
                    return await this.rpc("/llm/thread/get_response", {
                        thread_id: this.threadData.id,
                        content: content,
                    });
                },
            },
            hasLoadedMessages: true,
        };

        this.render();
    }
}

LLMChatDialog.components = { LLMThreadView };
LLMChatDialog.template = "llm.ChatDialog";

// Register the client action
registry.category("actions").add("llm_chat_dialog", LLMChatDialog);
