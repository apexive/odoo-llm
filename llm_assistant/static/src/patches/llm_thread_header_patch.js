/** @odoo-module **/

import { LLMThreadHeader } from "@llm_thread/components/llm_thread_header/llm_thread_header";
import { patch } from "@web/core/utils/patch";

/**
 * Minimal patch to add assistant functionality to existing thread header
 * Reuses all existing patterns and follows DRY principles
 */
patch(LLMThreadHeader.prototype, {
  setup() {
    super.setup();
    // Reuse existing store - it's already the patched version via useService
    this.assistantStore = this.llmStore;
  },

  /**
   * Get current assistant following existing pattern
   */
  get currentAssistant() {
    if (!this.assistantStore?.currentAssistant) return null;
    return this.assistantStore.currentAssistant;
  },

  /**
   * Get available assistants following existing pattern
   */
  get availableAssistants() {
    if (!this.assistantStore?._assistantsLoaded) return [];
    return Object.values(this.assistantStore.llmAssistants);
  },

  /**
   * Select assistant following existing update pattern
   * @param {Object} assistant - Assistant object to select
   */
  async selectAssistant(assistant) {
    if (!this.assistantStore) return;

    const assistantId = assistant ? assistant.id : null;
    if (assistantId === this.currentAssistant?.id) return;

    try {
      this.state.isLoadingUpdate = true;
      await this.assistantStore.selectAssistant(assistantId);
    } catch (error) {
      this.notification.add("Failed to update assistant", {
        type: "danger",
      });
      console.error("Error updating assistant:", error);
    } finally {
      this.state.isLoadingUpdate = false;
    }
  },

  /**
   * Clear assistant selection
   */
  async clearAssistant() {
    await this.selectAssistant(null);
  },
});
