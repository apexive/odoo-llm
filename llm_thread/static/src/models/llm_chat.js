/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'LLMChat',
    recordMethods: {
        async loadThread() {
            console.log('LLMChat: loadThread called', {
                exists: this.exists(),
                threadId: this.threadId,
                thread: this.thread,
                threadView: this.threadView
            });

            if (!this.exists()) {
                console.warn('LLMChat: Model no longer exists');
                return;
            }

            if (!this.threadId) {
                console.error('LLMChat: No threadId available');
                return;
            }

            console.log('LLMChat: Fetching thread data for ID:', this.threadId);
            let threadData;
            try {
                threadData = await this.messaging.rpc({
                    route: '/llm/thread/data',
                    params: {
                        thread_id: this.threadId,
                    },
                });
                console.log('LLMChat: Received thread data:', threadData);
                
                if (!threadData) {
                    console.error('LLMChat: No data received from server');
                    return;
                }

                if (threadData.error) {
                    console.error('LLMChat: Server returned error:', threadData.error);
                    return;
                }
            } catch (error) {
                console.error('LLMChat: RPC call failed:', error);
                return;
            }

            if (!this.exists()) {
                console.warn('LLMChat: Model no longer exists after RPC');
                return;
            }

            console.log('LLMChat: Processing thread data', {
                chatId: threadData.id,
                chatName: threadData.name,
                messageCount: threadData.messages?.length || 0,
                model: threadData.model,
                provider: threadData.provider
            });

            try {
                // Create base thread record if it doesn't exist
                const thread = this.messaging.models['Thread'].insert({
                    id: threadData.id,
                    model: 'llm.thread',
                    name: threadData.name,
                    message_needaction_counter: 0,
                });

                // Update thread cache
                const cache = this.messaging.models['ThreadCache'].insert({
                    messages: [],
                    thread: thread,
                });

                // Create thread viewer
                const threadViewer = this.messaging.models['ThreadViewer'].insert({
                    hasThreadView: true,
                    thread: thread,
                    threadCache: cache,
                });

                // Update chat state
                this.update({
                    name: threadData.name,
                    thread: thread,
                    threadViewer: threadViewer,
                });

                // Process messages
                if (threadData.messages?.length > 0) {
                    const messageCommands = threadData.messages.map(messageData => ({
                        id: messageData.id,
                        author: [['insert', { id: messageData.author }]],
                        body: messageData.content,
                        message_type: 'comment',
                    }));

                    this.messaging.models['Message'].insert(messageCommands);
                }

                console.log('LLMChat: Thread loaded successfully', {
                    currentName: this.name,
                    currentThread: this.thread,
                    currentThreadView: this.threadView,
                    messageCount: this.thread.messages.length
                });
            } catch (error) {
                console.error('LLMChat: Error updating thread:', error);
                throw error;
            }
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
        threadViewer: one('ThreadViewer', {
            compute() {
                if (!this.thread) {
                    return clear();
                }
                return {
                    hasThreadView: true,
                    thread: this.thread,
                };
            },
        }),
        threadView: one('ThreadView', {
            compute() {
                if (!this.threadViewer) {
                    return clear();
                }
                return this.threadViewer.threadView;
            },
        }),
    },
});