/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Service to handle real-time notifications for LLM generation jobs
 */
export class LLMGenerationJobNotificationService {
    constructor(env, { bus_service }) {
        this.env = env;
        this.busService = bus_service;
        this.activeThreadChannels = new Set();
        
        // Listen to bus messages
        this.busService.subscribe("llm_thread_update", this._onThreadUpdate.bind(this));
    }

    /**
     * Start listening to notifications for a specific thread
     * @param {number} threadId - The ID of the thread to listen to
     */
    subscribeToThread(threadId) {
        const channel = `llm_thread_${threadId}`;
        this.activeThreadChannels.add(channel);
        this.busService.addChannel(channel);
    }

    /**
     * Stop listening to notifications for a specific thread
     * @param {number} threadId - The ID of the thread to stop listening to
     */
    unsubscribeFromThread(threadId) {
        const channel = `llm_thread_${threadId}`;
        this.activeThreadChannels.delete(channel);
        this.busService.deleteChannel(channel);
    }

    /**
     * Handle thread update notifications
     * @param {Object} notification - The notification data
     */
    _onThreadUpdate(notification) {
        console.log("LLM Thread Update received:", notification);
        
        if (notification.type === 'new_message') {
            this._handleNewMessage(notification);
        }
    }

    /**
     * Handle new message notifications
     * @param {Object} notification - The notification data
     */
    _handleNewMessage(notification) {
        const { thread_id, message, job_id } = notification;
        
        // Trigger refresh of the thread if it's currently displayed
        this.env.bus.trigger('refresh_thread_messages', {
            threadId: thread_id,
            messageId: message.id,
            jobId: job_id
        });

        // Show a toast notification
        this.env.services.notification.add(
            `🎨 Generation job completed for thread ${thread_id}`, 
            {
                type: 'success',
                sticky: false,
                title: 'Generation Complete'
            }
        );
    }
}

// Register the service
registry.category("services").add("llm_generation_job_notification", {
    dependencies: ["bus_service", "notification"],
    start(env, deps) {
        return new LLMGenerationJobNotificationService(env, deps);
    },
});
