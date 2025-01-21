/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerPatch({
    name: 'ComposerView',
    fields: {
        hasAskAIButton: attr({
            compute() {
                return this.thread && this.thread.model === 'llm.thread';
            }
        }),
        isAskAIMode: attr({
            default: false,
        }),
    },
    recordMethods: {
        async onClickAskAI() {
            this.update({ isAskAIMode: true });
        },
        async onClickSendAskAI() {
            const content = this.textInputContent;
            if (!content) {
                return;
            }
            await this.async(() => this.postMessage({
                subtype_xmlid: 'llm_thread.mt_llm_question',
                content,
            }));
            this.update({
                isAskAIMode: false,
                textInputContent: clear(),
            });
        },
        onClickCancelAskAI() {
            this.update({
                isAskAIMode: false,
                textInputContent: clear(),
            });
        },
    },
});
