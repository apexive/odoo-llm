/** @odoo-module **/

import { LLMChatContainer } from "@llm_thread/components/llm_chat_container/llm_chat_container";
import { LLMMediaForm } from "../components/llm_media_form/llm_media_form";
import { patch } from "@web/core/utils/patch";

/**
 * Patch LLMChatContainer to check for media generation models
 */
patch(LLMChatContainer, {
  components: { ...LLMChatContainer.components, LLMMediaForm },
});

patch(LLMChatContainer.prototype, {
  /**
   * Check if a thread uses a media generation model
   * @param {Object} thread - The thread object from mailStore
   * @returns {Boolean}
   */
  isMediaGenerationModel(thread) {
    if (!thread?.id || !this.llmStore) {
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
});
