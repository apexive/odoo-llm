/** @odoo-module **/

import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/**
 * Patch Composer to add generation functionality for media generation models
 * Only affects llm.thread when model supports generation
 */
patch(Composer.prototype, {
  setup() {
    super.setup();

    // Initialize LLM store service
    try {
      this.llmStore = useService("llm.store");
    } catch (error) {
      console.warn("LLM store service not available:", error.message);
      this.llmStore = null;
    }
  },

  /**
   * Check if current thread is an LLM thread
   */
  get isLLMThread() {
    return this.props.composer?.thread?.model === "llm.thread";
  },

  /**
   * Check if the current LLM thread uses a media generation model
   */
  get isMediaGenerationModel() {
    if (!this.isLLMThread || !this.llmStore) {
      return false;
    }

    const thread = this.props.composer.thread;
    if (!thread?.id) {
      return false;
    }

    // Get model info from llmStore
    const modelId = thread.model_id?.id || thread.model_id;
    if (!modelId) {
      return false;
    }

    const model = this.llmStore.llmModels[modelId];
    if (!model) {
      return false;
    }

    // Check if model supports generation
    const modelUse = model.model_use;
    return modelUse === "generation" || modelUse === "image_generation";
  },

  /**
   * Post a generation message with body_json
   * Called by LLMMediaForm component
   * @param {Object} inputs - Generation inputs according to model schema
   * @param {Array} attachments - Array of attachment objects
   */
  async postUserGenerationMessageForLLM(inputs, attachments = []) {
    if (!this.isLLMThread || !this.llmStore) {
      console.error("Cannot post generation message: not an LLM thread");
      return;
    }

    const threadId = this.props.composer.thread.id;
    if (!threadId) {
      console.error("Cannot post generation message: no thread ID");
      return;
    }

    try {
      // Use llmStore to handle generation posting
      await this.llmStore.postGenerationMessage(threadId, inputs, attachments);
    } catch (error) {
      console.error("Error posting generation message:", error);
      throw error;
    }
  },
});
