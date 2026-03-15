/** @odoo-module **/

import { llmStoreService } from "@llm_thread/services/llm_store_service";
import { patch } from "@web/core/utils/patch";

/**
 * Minimal patch to add assistant functionality to existing LLM store
 * Reuses all existing patterns and infrastructure
 */
patch(llmStoreService, {
  start(env, services) {
    const llmStore = super.start(env, services);
    const { orm, notification, "mail.store": mailStore } = services;

    // Store the original getDataLoaders method
    const originalGetDataLoaders = llmStore.getDataLoaders.bind(llmStore);

    // Add assistant-specific properties directly
    llmStore.llmAssistants = {};
    llmStore._assistantsLoaded = false;

    // Define currentAssistant getter with proper context binding
    Object.defineProperty(llmStore, "currentAssistant", {
      get: function () {
        const activeThread = this.activeLLMThread;
        if (!activeThread?.assistant_id) return null;

        const assistantId =
          activeThread.assistant_id?.id || activeThread.assistant_id;
        const assistant = this.llmAssistants[assistantId];

        return assistant || activeThread.assistant_id;
      },
      enumerable: true,
      configurable: true,
    });

    // Add other methods using Object.assign
    Object.assign(llmStore, {
      async loadLLMAssistants() {
        try {
          const assistants = await orm.searchRead(
            "llm.assistant",
            [["active", "=", true]],
            ["id", "name", "is_public", "provider_id", "model_id", "tool_ids"]
          );

          assistants.forEach((assistant) => {
            this.llmAssistants[assistant.id] = assistant;
          });
          this._assistantsLoaded = true;
        } catch (error) {
          console.warn(
            "LLM assistants not available - llm_assistant module may not be installed:",
            error.message
          );
        }
      },

      async selectAssistant(assistantId) {
        const activeThread = this.activeLLMThread;
        if (!activeThread) {
          notification.add("No active thread to update", { type: "warning" });
          return;
        }

        try {
          // v17: Use jsonrpc instead of rpc import (doesn't exist in v17)
          const result = await env.services.rpc("/llm/thread/set_assistant", {
            thread_id: activeThread.id,
            assistant_id: assistantId,
          });

          if (!result.success && result.success !== undefined) {
            notification.add("Failed to update assistant", { type: "danger" });
            return;
          }

          // v17: Refresh thread data by re-reading from server
          // fetchData is on threadService, not thread, and doesn't support custom fields
          // Instead, read the updated thread data directly
          const threadData = await orm.read("llm.thread", [activeThread.id], [
            "name", "provider_id", "model_id", "tool_ids",
          ]);
          if (threadData.length > 0) {
            mailStore.Thread.insert({
              id: activeThread.id,
              model: "llm.thread",
              ...threadData[0],
            });
          }
        } catch (error) {
          console.error("Error selecting assistant:", error);
          notification.add("Failed to update assistant", { type: "danger" });
        }
      },

      // Extend existing getDataLoaders method instead of overriding initialize
      getDataLoaders() {
        const baseLoaders = originalGetDataLoaders();
        return [...baseLoaders, this.loadLLMAssistants];
      },
    });

    return llmStore;
  },
});
