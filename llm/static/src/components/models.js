/** @odoo-module **/

import { Record } from "@web/core/model";
import { EventBus } from "@odoo/owl";

/**
 * Base message model for handling chat messages
 */
export class MessageModel extends Record {
    setup(values) {
        super.setup();
        this.id = values.id;
        this.content = values.content;
        this.role = values.role;
        this.author = values.author;
        this.timestamp = values.timestamp;
        this.status = values.status || 'sent';
        this.error = null;
        this.isRetrying = false;
    }

    setError(error) {
        this.status = 'error';
        this.error = error;
        this.update({ status: this.status, error: this.error });
    }

    setRetrying() {
        this.isRetrying = true;
        this.status = 'sending';
        this.update({ isRetrying: true, status: this.status });
    }

    setSuccess() {
        this.status = 'sent';
        this.error = null;
        this.isRetrying = false;
        this.update({ status: this.status, error: null, isRetrying: false });
    }
}

/**
 * Thread model for managing chat thread data and operations
 */
export class ThreadModel extends Record {
    setup(values) {
        super.setup();
        this.id = values.id;
        this.name = values.name;
        this.provider = values.provider;
        this.model = values.model;
        this.isLoading = false;
        this.hasError = false;
        this.errorMessage = null;
        this.messages = new Map();
        this.messageOrder = [];
        this.eventBus = new EventBus();

        // Initialize messages
        if (values.messages) {
            values.messages.forEach(msg => this.addMessage(msg));
        }
    }

    addMessage(messageData) {
        const message = new MessageModel(this.env, messageData);
        this.messages.set(message.id, message);
        this.messageOrder.push(message.id);
        this.update({ messages: this.messages });
        this.eventBus.trigger('message-added', { message });
        return message;
    }

    async loadMessages() {
        if (this.isLoading) return;

        this.isLoading = true;
        this.update({ isLoading: true });

        try {
            const result = await this.env.services.rpc("/llm/thread/data", {
                thread_id: this.id,
            });

            // Clear existing messages
            this.messages.clear();
            this.messageOrder = [];

            // Add new messages
            result.messages.forEach(msg => this.addMessage(msg));

            this.hasError = false;
            this.errorMessage = null;
        } catch (error) {
            this.hasError = true;
            this.errorMessage = error.message || 'Failed to load messages';
            throw error;
        } finally {
            this.isLoading = false;
            this.update({
                isLoading: false,
                hasError: this.hasError,
                errorMessage: this.errorMessage
            });
        }
    }

    async postMessage(content, role = 'user') {
        const messageData = {
            id: `temp_${Date.now()}`,
            content,
            role,
            timestamp: new Date().toISOString(),
            status: 'sending'
        };

        const message = this.addMessage(messageData);

        try {
            const result = await this.env.services.rpc("/llm/thread/post_message", {
                thread_id: this.id,
                content,
                role,
            });

            // Update with server response
            message.setSuccess();
            return true;
        } catch (error) {
            message.setError(error.message || 'Failed to send message');
            throw error;
        }
    }

    async getAIResponse(content) {
        try {
            return await this.env.services.rpc("/llm/thread/get_response", {
                thread_id: this.id,
                content,
            });
        } catch (error) {
            throw new Error('Failed to get AI response: ' + (error.message || 'Unknown error'));
        }
    }

    getOrderedMessages() {
        return this.messageOrder.map(id => this.messages.get(id)).filter(Boolean);
    }
}

/**
 * Message list model for managing message display
 */
export class MessageListModel extends Record {
    setup(values) {
        super.setup();
        this.messages = values.messages || [];
        this.isLoading = false;
        this.hasMoreMessages = false;
        this.isLoadingMore = false;
        this.scrollTop = 0;
        this.scrollHeight = 0;
        this.isAtBottom = true;
        this.hasUnreadMessages = false;
        this.error = null;

        // Scroll position management
        this._lastScrollHeight = 0;
        this._shouldPreserveScroll = false;
        this._savedScrollPosition = 0;
    }

    saveScrollPosition(scrollTop, scrollHeight) {
        this._lastScrollHeight = scrollHeight;
        this._savedScrollPosition = scrollTop;
        this._shouldPreserveScroll = true;
    }

    async loadMoreMessages() {
        if (this.isLoadingMore || !this.hasMoreMessages) return;

        this.isLoadingMore = true;
        this.update({ isLoadingMore: true });

        try {
            // Implement pagination logic here
            await new Promise(resolve => setTimeout(resolve, 1000));
            this.hasMoreMessages = false;
        } catch (error) {
            this.error = error.message || 'Failed to load more messages';
        } finally {
            this.isLoadingMore = false;
            this.update({
                isLoadingMore: false,
                hasMoreMessages: this.hasMoreMessages,
                error: this.error
            });
        }
    }
}

/**
 * Composer model for managing message input
 */
export class ComposerModel extends Record {
    setup() {
        super.setup();
        this.textInputContent = "";
        this.isDisabled = false;
        this.shouldFocus = false;
        this.hasToRestoreContent = false;
        this.placeholder = "Type a message...";
        this.error = null;
    }

    setError(error) {
        this.error = error;
        this.update({ error: this.error });
    }

    clearError() {
        this.error = null;
        this.update({ error: null });
    }

    disable() {
        this.isDisabled = true;
        this.update({ isDisabled: true });
    }

    enable() {
        this.isDisabled = false;
        this.update({ isDisabled: false });
    }
}

/**
 * Thread view model that coordinates the overall chat UI
 */
export class ThreadViewModel extends Record {
    setup(values) {
        super.setup();
        this.thread = new ThreadModel(this.env, values.thread);
        this.messageListView = new MessageListModel(this.env, {
            messages: this.thread.getOrderedMessages(),
        });
        this.composer = new ComposerModel(this.env);
        this.hasLoadedMessages = values.hasLoadedMessages || false;
        this.hasError = false;
        this.errorMessage = "";

        // Subscribe to thread events
        this.thread.eventBus.addEventListener('message-added', this._onMessageAdded.bind(this));
    }

    _onMessageAdded({ detail: { message } }) {
        this.messageListView.update({
            messages: this.thread.getOrderedMessages()
        });
    }

    cleanup() {
        // Cleanup event listeners
        this.thread.eventBus.removeEventListener('message-added', this._onMessageAdded);
    }
}