/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { LegacyComponent } from '@web/legacy/legacy_component';

export class LLMChat extends LegacyComponent {
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
    }

    /**
     * @returns {LLMChat}
     */
    get chat() {
        return this.props.record;
    }
}

Object.assign(LLMChat, {
    props: { record: Object },
    template: 'llm.Chat',
});

registerMessagingComponent(LLMChat);