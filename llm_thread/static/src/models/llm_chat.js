/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'LLMChat',
    recordMethods: {
        /**
         * @returns {Thread}
         */
        async loadThread() {
            const threadData = await this.messaging.rpc({
                route: '/llm/thread/data',
                params: {
                    thread_id: this.threadId
                }
            });
            
            if (!this.exists()) {
                return;
            }

            this.update({
                thread: {
                    id: this.threadId,
                    model: 'llm.thread',
                    name: threadData.name,
                    messages: threadData.messages.map(msg => ({
                        id: msg.id,
                        body: msg.content,
                        author: {
                            id: msg.author_id || this.messaging.currentPartner.id,
                            name: msg.author
                        },
                        date: msg.timestamp,
                        llm_role: msg.role,
                        message_type: 'comment',
                    }))
                }
            });
        },

        /**
         * @param {string} content 
         */
        async sendMessage(content) {
            const message = await this.messaging.rpc({
                route: '/llm/thread/post_message',
                params: {
                    thread_id: this.threadId,
                    content: content,
                    role: 'user'
                }
            });

            // Start streaming response
            const eventSource = new EventSource(
                `/llm/thread/stream_response?thread_id=${this.threadId}`,
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
                    this.messaging.notify({
                        message: data.error,
                        type: 'danger',
                    });
                    eventSource.close();
                }
            };

            eventSource.onerror = () => {
                eventSource.close();
                this.messaging.notify({
                    message: "Error receiving AI response",
                    type: 'danger',
                });
            };
        },

        /**
         * @private
         * @param {string} content 
         */
        _updateAssistantMessage(content) {
            if (!this.exists()) {
                return;
            }

            const messages = [...this.thread.messages];
            const lastMessage = messages[messages.length - 1];

            if (lastMessage?.llm_role === 'assistant') {
                lastMessage.body = content;
                this.thread.update({ messages });
            } else {
                this.thread.update({
                    messages: [...messages, {
                        id: `temp_${Date.now()}`,
                        body: content,
                        author: {
                            id: -1,
                            name: 'Assistant'
                        },
                        date: new Date().toISOString(),
                        llm_role: 'assistant',
                        message_type: 'comment',
                    }]
                });
            }
        }
    },
    fields: {
        /**
         * States the OWL component of this chat
         */
        component: attr(),
        /**
         * ID of the thread being displayed
         */
        threadId: attr({
            identifying: true,
        }),
        /**
         * The thread containing messages
         */
        thread: one('Thread'),
        /**
         * View of the thread
         */
        threadView: one('ThreadView', {
            compute() {
                if (!this.thread) {
                    return clear();
                }
                return {
                    thread: this.thread,
                    hasComposer: true,
                    order: 'asc',
                };
            }
        }),
        messaging: one('Messaging', {
            compute() {
                return this.messaging;
            }
        }),
    },
});