/** @odoo-module **/

import { LLMChatComposer } from "@llm_thread/components/llm_chat_composer/llm_chat_composer";
import { patch } from "@web/core/utils/patch";

patch(LLMChatComposer.prototype, "llm_generate.llm_chat_composer_patch", {
  /**
   * @returns {Thread}
   */
  get thread() {
    return this.composerView?.composer?.activeThread;
  },

  /**
   * @returns {Boolean}
   */
  get isMediaGenerationModel() {
    if (!this.thread?.llmModel) {
      return false;
    }
    return this.thread.llmModel.isMediaGenerationModel === true;
  },

  /**
   * @returns {Boolean}
   */
  get isStreaming() {
    return this.thread?.composer?.isStreaming || false;
  },
});
