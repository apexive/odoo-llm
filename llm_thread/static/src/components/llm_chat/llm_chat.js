/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { LegacyComponent } from '@web/legacy/legacy_component';

export class LLMChat extends LegacyComponent {
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        
        // Debug setup
        console.log('LLMChat Component: Setup', {
            props: this.props,
            record: this.chat
        });
        
        // Watch for changes
        this.env.bus.on('LLMChat:thread-updated', this, () => {
            console.log('LLMChat Component: Thread Updated', {
                chat: this.chat,
                thread: this.chat?.thread,
                threadView: this.chat?.threadView
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
            thread: chat?.thread,
            threadView: chat?.threadView
        });
        return chat;
    }

    /**
     * Debugging method to check component state
     */
    debugRender() {
        console.log('LLMChat Component: Rendering', {
            chat: this.chat,
            hasThread: Boolean(this.chat?.thread),
            hasThreadView: Boolean(this.chat?.threadView),
            threadName: this.chat?.thread?.name,
            messageCount: this.chat?.thread?.messages?.length
        });
    }
}

Object.assign(LLMChat, {
    props: { record: Object },
    template: 'llm.Chat',
});

registerMessagingComponent(LLMChat);