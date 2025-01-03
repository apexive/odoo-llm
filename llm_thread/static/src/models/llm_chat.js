/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'LLMChat',
    recordMethods: {
        async loadThread() {
            if (!this.exists()) {
                return;
            }

            const threadData = await this.messaging.rpc({
                route: '/llm/thread/data',
                params: {
                    thread_id: this.threadId,
                },
            });

            if (!this.exists()) {
                return;
            }

            this.update({ name: threadData.name });
        },

        async sendMessage(content) {
            if (!this.thread) {
                return;
            }

            // Post user message and start streaming response
            await this.messaging.rpc({
                route: '/llm/thread/post_message',
                params: {
                    thread_id: this.threadId,
                    content: content,
                    role: 'user',
                },
            });

            // Start streaming AI response
            const eventSource = new EventSource(
                `/llm/thread/stream_response?thread_id=${this.threadId}`,
                { withCredentials: true }
            );

            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'error') {
                    this.messaging.notify({
                        message: data.error,
                        type: 'danger',
                    });
                    eventSource.close();
                }
                
                if (data.type === 'end') {
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
    },
    fields: {
        name: attr(),
        threadId: attr({
            identifying: true,
        }),
        thread: one('Thread', {
            compute() {
                if (!this.threadId) {
                    return clear();
                }
                return {
                    id: this.threadId,
                    model: 'llm.thread',
                };
            },
        }),
        discussViewer: one('ThreadViewer', {
            compute() {
                if (!this.thread) {
                    return clear();
                }
                return {
                    discuss: this.messaging.discuss,
                    hasThreadView: true,
                    thread: this.thread,
                };
            },
        }),
        threadView: one('ThreadView', {
            compute() {
                if (!this.discussViewer || !this.discussViewer.threadView) {
                    return clear();
                }
                return this.discussViewer.threadView;
            },
        }),
    },
});