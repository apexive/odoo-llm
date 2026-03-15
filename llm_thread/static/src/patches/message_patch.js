/** @odoo-module **/

import { LLMToolMessage } from "../components/llm_tool_message/llm_tool_message";
import { Message } from "@mail/core/common/message";
import { Message as MessageModel } from "@mail/core/common/message_model";
import { patch } from "@web/core/utils/patch";

/**
 * PATCH 1: Message Component Static Properties
 * Adds LLMToolMessage to the available components registry
 */
patch(Message, {
  components: { ...Message.components, LLMToolMessage },
});

/**
 * PATCH 2: Message Component Prototype Methods
 * Adds UI rendering logic and getters for LLM message detection and styling
 * These methods are used by the component template and rendering logic
 */
patch(Message.prototype, {
  /**
   * Check if this message is in an LLM thread
   */
  get isLLMMessage() {
    return this.props.message?.model === "llm.thread";
  },

  /**
   * Get LLM role for this message
   */
  get llmRole() {
    return this.props.message?.llm_role;
  },

  /**
   * Check if message is a tool message
   */
  get isToolMessage() {
    return this.isLLMMessage && this.llmRole === "tool";
  },

  /**
   * Check if assistant message has tool calls
   */
  get hasToolCalls() {
    return (
      this.isLLMMessage &&
      this.llmRole === "assistant" &&
      this.props.message?.body_json?.tool_calls?.length > 0
    );
  },

  /**
   * Add LLM-specific CSS classes
   */
  get className() {
    let className = super.className || "";

    if (this.isLLMMessage) {
      className += " o-llm-message";

      if (this.llmRole) {
        className += ` o-llm-message-${this.llmRole}`;
      }

      // Add streaming class for assistant messages that are still being generated
      if (this.llmRole === "assistant" && this.props.message?.isPending) {
        className += " o-llm-message-streaming";
      }
    }

    return className;
  },
});

/**
 * PATCH 3: Message Model (Data Layer)
 * Patches the Message data model to handle LLM-specific isEmpty computation
 * This ensures LLM messages with tool calls or body_json are never filtered out
 * NOTE: This is NOT the component - this is the data model that holds message data
 *
 * v17: Uses get isEmpty() getter instead of computeIsEmpty() method
 */
patch(MessageModel.prototype, {
  /**
   * Override isEmpty getter for LLM messages with tool calls or body_json
   * @returns {Boolean} True if message is empty
   */
  get isEmpty() {
    // For LLM messages, apply custom logic
    if (this.model === "llm.thread") {
      // Assistant messages with tool calls are never empty
      if (
        this.llm_role === "assistant" &&
        this.body_json?.tool_calls?.length > 0
      ) {
        return false;
      }

      // Tool messages with body_json are never empty
      if (this.llm_role === "tool" && this.body_json) {
        return false;
      }
    }

    // Use original computation for other messages
    return super.isEmpty;
  },
});
