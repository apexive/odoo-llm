/** @odoo-module **/

import { Component, useRef } from "@odoo/owl";
import { markdownToHtml } from "@web/core/utils/markdown";
import { useService } from "@web/core/utils/hooks";

export class LLMMessage extends Component {
  setup() {
    super.setup();
    this.contentRef = useRef("content");
    this.prettyBodyRef = useRef("prettyBody");
    this.notification = useService("notification");
  }

  get message() {
    return this.props.message;
  }

  get isUserMessage() {
    return this.message.role === "user";
  }

  get authorName() {
    return this.isUserMessage ?
        this.env.session.name :
        (this.message.author || "Assistant");
  }

  get formattedDate() {
    if (!this.message.timestamp) return "";

    try {
      return new Date(this.message.timestamp).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit"
      });
    } catch (error) {
      return "";
    }
  }

  get statusClass() {
    switch (this.message.status) {
      case 'sending':
        return 'text-muted';
      case 'error':
        return 'text-danger';
      case 'sent':
      default:
        return '';
    }
  }

  get showRetry() {
    return this.message.status === 'error';
  }

  async onContentMounted() {
    if (!this.contentRef.el || !this.prettyBodyRef.el || !this.message.content) {
      return;
    }

    try {
      const html = await markdownToHtml(this.message.content);
      if (this.prettyBodyRef.el) {
        this.prettyBodyRef.el.innerHTML = html;

        // Add syntax highlighting if needed
        if (window.Prism) {
          this.prettyBodyRef.el.querySelectorAll('pre code').forEach((block) => {
            window.Prism.highlightElement(block);
          });
        }
      }
    } catch (error) {
      this.notification.notify({
        title: "Error",
        message: "Failed to render message content",
        type: "danger"
      });

      // Fallback to plain text
      if (this.prettyBodyRef.el) {
        this.prettyBodyRef.el.textContent = this.message.content;
      }
    }
  }

  onRetryClick() {
    this.env.messageBus.trigger('message-retry', {
      messageId: this.message.id
    });
  }
}

LLMMessage.template = "llm.Message";
LLMMessage.props = {
  message: {
    type: Object,
    shape: {
      id: [String, Number],
      content: String,
      role: String,
      author: { type: String, optional: true },
      timestamp: { type: String, optional: true },
      status: { type: String, optional: true },
      error: { type: String, optional: true }
    }
  },
  className: { type: String, optional: true },
};
