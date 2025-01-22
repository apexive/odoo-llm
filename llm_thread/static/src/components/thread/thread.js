/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

import '@mail/models/composer_view';
import session from "web.session";
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';


import { sprintf } from '@web/core/utils/strings';



registerPatch({
    name: 'ComposerView',
    fields: {
        isAiThinking: attr({
            default: false,
        }),
    },
    recordMethods: {
        onClickAskAI: async function() {
            await this._sendQuestionForAi();
        },

        updateIsAiThinking: function(isAiThinking) {
            this.update({ isAiThinking });
        },

        async _sendQuestionForAi(){
            this.updateIsAiThinking(true);
            const composer = this.composer;
            const postData = this._getMessageData();
            const params = {
                'post_data': postData,
                'thread_id': composer.thread.id,
                'thread_model': composer.thread.model,
            };
            try {
                composer.update({ isPostingMessage: true });
                
                Object.assign(postData, {
                    subtype_xmlid: 'llm_thread.mt_llm_question',
                });
                
                if (this.threadView && this.threadView.replyingToMessageView && this.threadView.thread !== this.messaging.inbox.thread) {
                    postData.parent_id = this.threadView.replyingToMessageView.message.id;
                }
                params.context = Object.assign(params.context || {}, session.user_context);
                const { threadView = {} } = this;
                const chatter = this.chatter;
                const { thread: chatterThread } = this.chatter || {};
                const { thread: threadViewThread } = threadView;
                // Keep a reference to messaging: composer could be
                // unmounted while awaiting the prc promise. In this
                // case, this would be undefined.
                const messaging = this.messaging;
                const messageData = await this.messaging.rpc({ route: `/mail/message/post`, params });
                if (!messaging.exists()) {
                    return;
                }
                const message = messaging.models['Message'].insert(
                    messaging.models['Message'].convertData(messageData)
                );
                if (messaging.hasLinkPreviewFeature && !message.isBodyEmpty) {
                    messaging.rpc({
                        route: `/mail/link_preview`,
                        params: {
                            message_id: message.id
                        }
                    }, { shadow: true });
                }
                for (const threadView of message.originThread.threadViews) {
                    // Reset auto scroll to be able to see the newly posted message.
                    threadView.update({ hasAutoScrollOnMessageReceived: true });
                    threadView.addComponentHint('message-posted', { message });
                }
                if (chatter && chatter.exists() && chatter.hasParentReloadOnMessagePosted && messageData.recipients.length) {
                    chatter.reloadParentView();
                }
                if (chatterThread) {
                    if (this.exists()) {
                        this.delete();
                    }
                    if (chatterThread.exists()) {
                        // Load new messages to fetch potential new messages from other users (useful due to lack of auto-sync in chatter).
                        chatterThread.fetchData(['followers', 'messages', 'suggestedRecipients']);
                    }
                }
                if (threadViewThread) {
                    if (threadViewThread === messaging.inbox.thread) {
                        messaging.notify({
                            message: sprintf(messaging.env._t(`Message posted on "%s"`), message.originThread.displayName),
                            type: 'info',
                        });
                        if (this.exists()) {
                            this.updateIsAiThinking(false);
                            this.delete();
                        }
                    }
                    if (threadView && threadView.exists()) {
                        console.log('Cleared replying to message view');
                        threadView.update({ replyingToMessageView: clear() });
                    }
                }
                if (composer.exists()) {
                    composer._reset();
                }
            } catch (e) { console.error(e); }
            finally {
                if (composer.exists()) {
                    composer.update({ isPostingMessage: false });
                }
            }
        }
    },
});
