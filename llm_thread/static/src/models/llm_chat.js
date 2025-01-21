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
                console.log('LLMChat: Starting thread creation');
                
                // Create the thread first
                const thread = await this.messaging.models['Thread'].insert({
                    id: threadData.id,
                    model: 'llm.thread',
                    name: threadData.name,
                });
                
                console.log('LLMChat: Thread created', { thread });

                // Create thread cache with messages
                const messageRecords = threadData.messages.map(msg => {
                    const messageData = {
                        id: msg.id,
                        body: msg.content,
                        date: moment(msg.timestamp),
                        message_type: 'message',
                        // model: 'llm.thread',
                        // llmRole: msg.role,
                    };

                    // Handle author information differently for AI vs human messages
                    if (msg.role === 'assistant') {
                        // messageData.author_id = false;  // No partner for AI messages
                        messageData.email_from = msg.author;  // Use as display name
                    } else if (msg.role === 'user') {
                        messageData.author = this.messaging.currentPartner;
                    }

                    return messageData;
                });

                // Insert messages
                const messages = await this.messaging.models['Message'].insert(messageRecords);
                
                console.log('LLMChat: Messages created', { 
                    messageCount: messages.length,
                    firstMessage: messages[0] 
                });

                // Create cache with messages
                const cache = await this.messaging.models['ThreadCache'].insert({
                    isLoaded: true,
                    thread: [['replace', thread]], // Use replace instead of link
                    rawFetchedMessages: [['replace', messages]], // Use replace for messages
                });

                console.log('LLMChat: Cache created', {
                    cache,
                    hasMessages: cache.rawFetchedMessages.length 
                });

                // Create ThreadViewer with everything linked
                const threadViewer = await this.messaging.models['ThreadViewer'].insert({
                    hasThreadView: true,
                    thread: [['replace', thread]], // Use replace for thread
                    threadCache: [['replace', cache]], // Use replace for cache
                    order: 'desc',
                });

                console.log('ThreadViewer created', {
                    thread: threadViewer.thread,
                    threadCache: threadViewer.threadCache,
                    messageListView: threadViewer.threadView?.messageListView
                });

                // Finally update thread 
                // Defensive update with fallback
                try {
                     // Use a different update strategy
                    // this.messaging.models['LLMChat'].update(
                    //     this, // Current record
                    //     {
                    //         name: threadData.name,
                    //         thread: thread, // Direct reference instead of link command
                    //         threadViewer: threadViewer,
                    //     },
                    //     { 
                    //         // Optional: add context or additional options
                    //         allowWriteNull: true 
                    //     }
                    // );

                    // Alternative approach
                    // Object.assign(this, {
                    //     name: threadData.name,
                    //     thread,
                    //     threadViewer,
                    // });
                    await this.update({
                        name: threadData.name,
                        threadId: threadData.id, // This will trigger the computed fields
                        thread: [['link', thread.id]],
                        threadViewer: [['link', threadViewer.id]],
                    });
                } catch (updateError) {
                    console.error('Error updating LLMChat:', updateError);
                    throw updateError;
                }

                // Fire event to trigger re-render in container
                this.messaging.messagingBus.trigger('o-thread-loaded');

            } catch (error) {
                console.error('LLMChat: Error creating thread:', error);
                throw error;
            }
        }
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