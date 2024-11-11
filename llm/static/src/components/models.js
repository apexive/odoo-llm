/** @odoo-module **/

import { registerModel } from "@mail/model/model_core";
import { attr, many, one } from "@mail/model/model_field";
import { clear } from "@mail/model/model_field_command";

registerModel({
  name: "LLMMessage",
  fields: {
    id: attr({
      identifying: true,
    }),
    content: attr({
      default: "",
    }),
    role: attr({
      default: "user",
    }),
    author: attr(),
    timestamp: attr({
      default: () => new Date().toISOString(),
    }),
    status: attr({
      default: "sent",
    }),
    error: attr({
      default: null,
    }),
    thread: one("LLMThread", {
      inverse: "messages",
    }),
    isAuthor: attr({
      compute() {
        return this.author?.id === this.messaging.currentPartner?.id;
      },
      default: false,
    }),
    formattedTime: attr({
      compute() {
        if (!this.timestamp) {
          return "";
        }
        return new Date(this.timestamp).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        });
      },
    }),
  },
  recordMethods: {
    setError(error) {
      this.update({
        status: "error",
        error: error.message || "Unknown error",
      });
    },
    setSuccess() {
      this.update({
        status: "sent",
        error: null,
      });
    },
  },
});

registerModel({
  name: "LLMThread",
  fields: {
    id: attr({
      identifying: true,
    }),
    name: attr({
      default: "",
    }),
    messages: many("LLMMessage", {
      inverse: "thread",
    }),
    isLoading: attr({
      default: false,
    }),
    hasError: attr({
      default: false,
    }),
    errorMessage: attr({
      default: null,
    }),
    // Changed from one('llm.provider') to attr() since we'll store provider data as attributes
    provider: attr({
      default: null,
    }),
    // Changed from one('llm.model') to attr() since we'll store model data as attributes
    model: attr({
      default: null,
    }),
    composer: one("LLMComposer", {
      inverse: "thread",
    }),
    lastMessage: one("LLMMessage", {
      compute() {
        const { length, [length - 1]: lastMessage } = this.messages;
        return lastMessage || clear();
      },
    }),
    isEmpty: attr({
      compute() {
        return this.messages.length === 0;
      },
      default: true,
    }),
    threadViews: many("LLMThreadView", {
      inverse: "thread",
    }),
  },
  recordMethods: {
    async loadMessages() {
      if (this.isLoading) {
        return;
      }

      this.update({ isLoading: true });

      try {
        const result = await this.env.services.rpc("/llm/thread/data", {
          thread_id: this.id,
        });

        this.messaging.models.LLMMessage.insert(
          result.messages.map((data) => ({
            ...data,
            thread: this,
          }))
        );

        // Update provider and model data
        this.update({
          provider: result.provider,
          model: result.model,
          hasError: false,
          errorMessage: null,
        });
      } catch (error) {
        this.update({
          hasError: true,
          errorMessage: error.message || "Failed to load messages",
        });
        throw error;
      } finally {
        this.update({ isLoading: false });
      }
    },

    async sendMessage(content, role = "user") {
      const message = this.messaging.models.LLMMessage.insert({
        content,
        role,
        status: "sending",
        thread: this,
      });

      try {
        await this.env.services.rpc("/llm/thread/post_message", {
          thread_id: this.id,
          content,
          role,
        });

        message.setSuccess();
        return true;
      } catch (error) {
        message.setError(error);
        throw error;
      }
    },
  },
});

registerModel({
  name: "LLMComposer",
  fields: {
    content: attr({
      default: "",
    }),
    isDisabled: attr({
      default: false,
    }),
    placeholder: attr({
      default: "Type a message...",
    }),
    error: attr({
      default: null,
    }),
    thread: one("LLMThread", {
      inverse: "composer",
    }),
    threadView: one("LLMThreadView", {
      inverse: "composer",
    }),
    isEmpty: attr({
      compute() {
        return !this.content?.trim().length;
      },
      default: true,
    }),
    canSubmit: attr({
      compute() {
        return !this.isDisabled && !this.isEmpty;
      },
      default: false,
    }),
  },
  recordMethods: {
    clear() {
      this.update({
        content: "",
        error: null,
      });
    },

    disable() {
      this.update({ isDisabled: true });
    },

    enable() {
      this.update({
        isDisabled: false,
        error: null,
      });
    },

    setError(error) {
      this.update({
        error: error.message || "Unknown error",
      });
    },
  },
});

registerModel({
  name: "LLMThreadView",
  fields: {
    thread: one("LLMThread", {
      identifying: true,
      inverse: "threadViews",
    }),
    composer: one("LLMComposer", {
      compute() {
        if (!this.thread) {
          return clear();
        }
        return {};
      },
      inverse: "threadView",
    }),
    isLoading: attr({
      related: "thread.isLoading",
    }),
    hasError: attr({
      related: "thread.hasError",
    }),
    errorMessage: attr({
      related: "thread.errorMessage",
    }),
    messages: many("LLMMessage", {
      related: "thread.messages",
    }),
    lastMessage: one("LLMMessage", {
      related: "thread.lastMessage",
    }),
    scrollPosition: attr({
      default: 0,
    }),
    isAtBottom: attr({
      default: true,
    }),
    hasUnreadMessages: attr({
      compute() {
        return !this.isAtBottom && this.messages.length > 0;
      },
      default: false,
    }),
  },
  recordMethods: {
    updateScroll(position, isAtBottom) {
      this.update({
        scrollPosition: position,
        isAtBottom,
      });
    },
  },
});
