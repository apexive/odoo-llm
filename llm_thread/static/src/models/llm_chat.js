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
            const env = this.messaging.env;
            const threadData = await env.services.rpc('/llm/thread/data', {
                thread_id: this.threadId
            });

            if (!this.exists()) {
                return;
            }

            this.update({
                thread: {
                    id: this.threadId,
                    model: 'llm.thread',
                    name: threadData.name,
                    message_ids: threadData.messages.map(msg => ({
                        id: msg.id,
                        body: msg.content,
                        author: {
                            id: msg.author_id || this.messaging.currentPartner.id,
                            name: msg.author
                        },
                        date: msg.timestamp,
                        message_type: 'comment',
                        attachments: [],
                    }))
                },
            });

            // Initialize the thread viewer and view after thread is set
            if (this.thread) {
                this.update({
                    threadViewer: {
                        thread: this.thread,
                        hasComposer: true,
                    },
                });
            }
        },

        /**
         * @param {string} content 
         */
        async sendMessage(content) {
            const env = this.messaging.env;
            await env.services.rpc('/llm/thread/post_message', {
                thread_id: this.threadId,
                content: content,
                role: 'user'
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
                    env.services.notification.add(data.error, {
                        type: 'danger',
                    });
                    eventSource.close();
                }
            };

            eventSource.onerror = () => {
                eventSource.close();
                env.services.notification.add("Error receiving AI response", {
                    type: 'danger',
                });
            };
        },

        /**
         * @private
         * @param {string} content 
         */
        _updateAssistantMessage(content) {
            if (!this.exists() || !this.thread) {
                return;
            }

            const messages = [...this.thread.message_ids];
            const lastMessage = messages[messages.length - 1];

            if (lastMessage?.is_ai_response) {
                lastMessage.body = content;
                this.thread.update({ message_ids: messages });
            } else {
                this.thread.update({
                    message_ids: [...messages, {
                        id: `temp_${Date.now()}`,
                        body: content,
                        author: {
                            id: -1,
                            name: 'Assistant'
                        },
                        date: new Date().toISOString(),
                        is_ai_response: true,
                        message_type: 'comment',
                        attachments: [],
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
         * Viewer of the thread
         */
        threadViewer: one('ThreadViewer', {
            compute() {
                if (!this.thread) {
                    return clear();
                }
                return {
                    thread: this.thread,
                    hasComposer: true,
                };
            },
        }),

        /**
         * View of the thread
         */
        threadView: one('ThreadView', {
            compute() {
                if (!this.threadViewer) {
                    return clear();
                }
                return {
                    threadViewer: this.threadViewer,
                    hasComposer: true,
                    order: 'asc',
                    showTypingStatus: false,
                };
            },
        }),
    },
});