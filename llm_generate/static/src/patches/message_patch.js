/** @odoo-module **/

import { Message } from "@mail/core/common/message";
import { patch } from "@web/core/utils/patch";

/**
 * Patch Message Component to add generation-specific properties
 * Extends the message display for generation inputs and outputs
 */
patch(Message.prototype, {
  /**
   * Check if this is an LLM user message with generation data
   */
  get isLLMUserGenerationMessage() {
    const message = this.props.message;
    return (
      message?.model === "llm.thread" &&
      message?.llm_role === "user" &&
      message?.body_json &&
      Object.keys(message.body_json).length > 0
    );
  },

  /**
   * Check if this is an LLM assistant message with generation data
   * Excludes tool_calls which are handled separately
   */
  get isLLMAssistantGenerationMessage() {
    const message = this.props.message;
    // Exclude tool calls from generation output display
    return (
      message?.model === "llm.thread" &&
      message?.llm_role === "assistant" &&
      message?.body_json &&
      Object.keys(message.body_json).length > 0 &&
      !message?.body_json?.tool_calls
    );
  },

  /**
   * Get formatted generation input data for display (user messages)
   */
  get generationDataFormatted() {
    const message = this.props.message;
    if (!message?.body_json) {
      return "";
    }

    try {
      return JSON.stringify(message.body_json, null, 2);
    } catch (error) {
      console.error("Error formatting generation data:", error);
      return String(message.body_json);
    }
  },

  /**
   * Get formatted generation output data for display (assistant messages)
   */
  get generationOutputFormatted() {
    const message = this.props.message;
    if (!message?.body_json) {
      return "";
    }

    try {
      return JSON.stringify(message.body_json, null, 2);
    } catch (error) {
      console.error("Error formatting generation output:", error);
      return String(message.body_json);
    }
  },
});
