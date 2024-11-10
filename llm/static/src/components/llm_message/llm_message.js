/** @odoo-module **/

import { Component, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

/**
 * Message component for displaying LLM chat messages
 */
export class LLMMessage extends Component {
  setup() {
    this.contentRef = useRef("content");
    this.prettyBodyRef = useRef("prettyBody");
    this.notification = useService("notification");
    this.markdownService = useService("markdownService");
  }

  /**
   * @returns {Object} The LLMMessage record from props
   */
  get message() {
    return this.props.record;
  }

  /**
   * @returns {boolean} True if message is from user
   */
  get isUserMessage() {
    return this.message.role === "user";
  }

  /**
   * @returns {string} Name of message author
   */
  get authorName() {
    if (this.isUserMessage) {
      return this.env.session.name;
    }
    return this.message.author || "Assistant";
  }

  /**
   * @returns {string} Formatted timestamp
   */
  get formattedDate() {
    return this.message.formattedTime;
  }

  /**
   * @returns {string} CSS class based on message status
   */
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

  /**
   * @returns {boolean} Whether to show retry button
   */
  get showRetry() {
    return this.message.status === 'error';
  }

  /**
   * Handle mounting of content - renders markdown and code blocks
   */
  async onContentMounted() {
    if (!this.contentRef.el || !this.prettyBodyRef.el || !this.message.content) {
      return;
    }

    try {
      // Convert markdown to HTML if markdown service is available
      if (this.markdownService) {
        const html = await this.markdownService.convertToHtml(this.message.content);
        this.prettyBodyRef.el.innerHTML = html;
      } else {
        // Fallback to plain text if no markdown service
        this.prettyBodyRef.el.textContent = this.message.content;
      }

      // Handle code blocks if any
      const codeBlocks = this.prettyBodyRef.el.querySelectorAll('pre code');
      if (window.hljs && codeBlocks.length) {
        codeBlocks.forEach(block => {
          window.hljs.highlightElement(block);
        });
      }
    } catch (error) {
      // Fallback to plain text on error
      this.prettyBodyRef.el.textContent = this.message.content;
      console.error("Error rendering message content:", error);
    }
  }

  /**
   * Handle retry button click
   */
  onRetryClick() {
    if (this.props.onRetry) {
      this.props.onRetry(this.message);
    }
  }

  /**
   * Handle copy button click
   */
  async onCopyClick() {
    try {
      await navigator.clipboard.writeText(this.message.content);
      this.notification.add(this.env._t("Copied to clipboard"), {
        type: 'success',
        sticky: false,
      });
    } catch (error) {
      this.notification.add(this.env._t("Failed to copy message"), {
        type: 'danger',
        sticky: false,
      });
    }
  }
}

LLMMessage.template = "llm.Message";

LLMMessage.props = {
  record: {
    type: Object,
    required: true,
  },
  className: {
    type: String,
    optional: true,
  },
  onRetry: {
    type: Function,
    optional: true,
  },
};

// Register the component
registry.category("components").add("LLMMessage", LLMMessage);
