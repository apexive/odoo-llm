/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { LegacyComponent } from '@web/legacy/legacy_component';
import { onWillRender, onWillStart, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// Import ThreadView component
import { ThreadView } from '@mail/components/thread_view/thread_view';

export class LLMChat extends LegacyComponent {
    setup() {
        super.setup();
        
        // Use messaging service from hooks
        this.messagingService = useService('messaging');
        
        // Ensure messaging service is available before proceeding
        if (!this.messagingService) {
            console.error('Messaging service not available');
            return;
        }

        // Debug setup state
        console.log('LLMChat Component: Setup', {
            props: this.props,
            record: this.chat
        });
        
        onWillStart(async () => {
            try {
                const messaging = await this.messagingService.get();
                console.log('Messaging service initialized', messaging);
            } catch (error) {
                console.error('Failed to initialize messaging service', error);
            }
        });

        onWillRender(() => {
            console.log('LLMChat Component: Will Render', {
                chat: this.chat,
                thread: this.chat?.thread,
                threadView: this.chat?.threadView,
                name: this.chat?.name,
                messageCount: this.chat?.thread?.messages?.length,
                hasThread: Boolean(this.chat?.thread),
                hasThreadView: Boolean(this.chat?.threadView),
                threadViewType: this.chat?.threadView?.constructor?.name,
            });
        });

        onMounted(() => {
            console.log('LLMChat Component: Mounted', {
                chat: this.chat,
                thread: this.chat?.thread,
                threadView: this.chat?.threadView,
                element: this.el,
            });
        });
    }

    /**
     * @returns {LLMChat}
     */
    get chat() {
        const chat = this.props.record;
        console.log('LLMChat Component: Get chat', {
            chat,
            hasThread: Boolean(chat?.thread),
            hasThreadView: Boolean(chat?.threadView),
            threadId: chat?.threadId,
            threadType: chat?.thread?.constructor?.name,
            threadViewType: chat?.threadView?.constructor?.name,
        });
        return chat;
    }
}

// Register the LLMChat component
registerMessagingComponent(LLMChat);

// Add ThreadView to the component's static properties
LLMChat.components = { ThreadView };

Object.assign(LLMChat, {
    props: { record: Object },
    template: 'llm.Chat',
});