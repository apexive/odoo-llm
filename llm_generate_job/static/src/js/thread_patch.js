/** @odoo-module **/

import { LLMChatThread } from "@llm_thread/components/llm_chat_thread/llm_chat_thread";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(LLMChatThread.prototype, {
    setup() {
        super.setup();
        this.llmNotificationService = useService("llm_generation_job_notification");
        this.busService = useService("bus_service");
        
        onMounted(() => {
            this._subscribeToThreadNotifications();
        });
        
        onWillUnmount(() => {
            this._unsubscribeFromThreadNotifications();
        });
        
        // Listen for thread refresh events
        this.env.bus.addEventListener('refresh_thread_messages', this._onRefreshThreadMessages.bind(this));
    },

    /**
     * Subscribe to real-time notifications for this thread
     */
    _subscribeToThreadNotifications() {
        if (this.thread?.id) {
            this.llmNotificationService.subscribeToThread(this.thread.id);
            console.log(`Subscribed to notifications for thread ${this.thread.id}`);
        }
    },

    /**
     * Unsubscribe from real-time notifications for this thread
     */
    _unsubscribeFromThreadNotifications() {
        if (this.thread?.id) {
            this.llmNotificationService.unsubscribeFromThread(this.thread.id);
            console.log(`Unsubscribed from notifications for thread ${this.thread.id}`);
        }
    },

    /**
     * Handle thread refresh events
     * @param {CustomEvent} event - The refresh event
     */
    _onRefreshThreadMessages(event) {
        const { threadId, messageId, jobId } = event.detail;
        
        // Only refresh if this is the current thread
        if (this.thread?.id === threadId) {
            console.log(`Refreshing messages for thread ${threadId}, new message: ${messageId}`);
            
            // Force refresh the thread messages
            if (this.thread.refreshMessages) {
                this.thread.refreshMessages();
            } else {
                // Fallback: trigger a full thread reload
                this._reloadThread();
            }
        }
    },

    /**
     * Reload the entire thread data
     */
    async _reloadThread() {
        try {
            if (this.thread?.id) {
                // Trigger thread reload through the store
                const threadData = await this.env.services.orm.call(
                    'llm.thread',
                    'read',
                    [this.thread.id],
                    { fields: ['message_ids'] }
                );
                
                // Update the thread object if possible
                if (threadData && threadData.length > 0) {
                    // This would need to be adapted based on your thread model structure
                    console.log('Thread reloaded with new data');
                }
            }
        } catch (error) {
            console.error('Failed to reload thread:', error);
        }
    }
});
