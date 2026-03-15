/** @odoo-module **/

import { Thread } from "@mail/core/common/thread";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/**
 * Patch Thread component to handle LLM-specific message rendering and styling
 * Only affects llm.thread models, preserves all normal mail functionality
 */
patch(Thread.prototype, {
  setup() {
    super.setup();
    // v17: useService must be called in setup(), not lazily
    try {
      this._llmStore = useService("llm.store");
    } catch (error) {
      this._llmStore = null;
    }
  },

  get llmStore() {
    return this._llmStore;
  },

  /**
   * Check if current thread is an LLM thread
   */
  get isLLMThread() {
    return this.props.thread?.model === "llm.thread";
  },

  /**
   * Check if thread is currently streaming
   */
  get isStreaming() {
    if (!this.isLLMThread) return false;
    return this.llmStore?.getStreamingStatus() || false;
  },

  /**
   * Override getMessageClass to add LLM-specific styling
   * @param {Object} message - Message object
   * @returns {String} CSS class names for the message
   */
  getMessageClass(message) {
    let className = super.getMessageClass ? super.getMessageClass(message) : "";

    if (this.isLLMThread && message.llm_role) {
      className += ` o-llm-message o-llm-message-${message.llm_role}`;

      // Add streaming indicator for assistant messages
      if (message.llm_role === "assistant" && message.isPending) {
        className += " o-llm-message-streaming";
      }
    }

    return className;
  },

  /**
   * Override message rendering for LLM threads
   * @param {Object} message - Message object
   * @returns {String} Rendered message HTML
   */
  renderMessage(message) {
    if (this.isLLMThread) {
      // For LLM threads, we might want to process markdown or add special formatting
      const renderedMessage = super.renderMessage
        ? super.renderMessage(message)
        : message;

      // Add LLM-specific message processing here if needed
      // For now, just return the standard rendered message
      return renderedMessage;
    }

    // Use original rendering for non-LLM threads
    return super.renderMessage ? super.renderMessage(message) : message;
  },

  /**
   * Override scrollToBottom to handle streaming messages
   */
  scrollToBottom() {
    super.scrollToBottom?.();

    // For LLM threads, ensure we scroll when new chunks arrive
    if (this.isLLMThread && this.isStreaming) {
      // Scroll after a short delay to account for content updates
      setTimeout(() => {
        super.scrollToBottom?.();
      }, 100);
    }
  },

  /**
   * Add LLM-specific CSS classes to thread container
   */
  get className() {
    let className = super.className || "";

    if (this.isLLMThread) {
      className += " o-llm-thread";

      if (this.isStreaming) {
        className += " o-llm-thread-streaming";
      }
    }

    return className;
  },

  /**
   * Override isSquashed to prevent squashing messages with different LLM roles
   * This ensures user, assistant, and tool messages appear in separate bubbles
   * @param {Object} msg - Current message
   * @param {Object} prevMsg - Previous message
   * @returns {Boolean} Whether messages should be squashed together
   */
  isSquashed(msg, prevMsg) {
    // For LLM threads, don't squash messages with different roles
    if (this.isLLMThread && prevMsg && msg.llm_role && prevMsg.llm_role) {
      if (msg.llm_role === prevMsg.llm_role) {
        // Different LLM roles should not be squashed
        return true;
      }
      return false;
    }

    // Use original squashing logic for everything else
    return super.isSquashed(msg, prevMsg);
  },
});
