/** @odoo-module **/

import { llmStoreService } from "@llm_thread/services/llm_store_service";
import { patch } from "@web/core/utils/patch";

/**
 * Patch to add generation functionality to existing LLM store
 * Follows the same pattern as llm_assistant module
 */
patch(llmStoreService, {
  start(env, services) {
    const llmStore = super.start(env, services);
    const { orm, notification, "mail.store": mailStore } = services;

    // Add generation-specific methods
    Object.assign(llmStore, {
      /**
       * Post a generation request with body_json containing inputs
       * @param {Number} threadId - Thread ID
       * @param {Object} inputs - Generation inputs according to model schema
       * @param {Array} attachments - Array of attachment objects
       */
      async postGenerationMessage(threadId, inputs, attachments = []) {
        const thread = mailStore.Thread.get({
          model: "llm.thread",
          id: threadId,
        });

        if (!thread) {
          notification.add("Thread not found", { type: "warning" });
          return;
        }

        // Check if model supports generation
        const modelId = thread.model_id?.id || thread.model_id;
        const model = this.llmModels[modelId];
        if (!model?.model_use?.includes("generation")) {
          notification.add("Selected model does not support generation", {
            type: "warning",
          });
          return;
        }

        try {
          const messageBody = inputs.prompt || "Content Generation Request";

          // Prepare attachment_ids
          const attachment_ids =
            attachments.length > 0 ? attachments.map((att) => att.id) : [];

          // Post user message with body_json
          await orm.call("llm.thread", "message_post", [threadId], {
            body: messageBody,
            body_json: inputs,
            llm_role: "user",
            attachment_ids: attachment_ids,
          });

          // Start generation streaming
          await this.startGenerationStreaming(threadId);
        } catch (error) {
          console.error("Error posting generation message:", error);
          notification.add("Failed to post generation message", {
            type: "danger",
          });
        }
      },

      /**
       * Start generation streaming for a thread
       * @param {Number} threadId - Thread ID
       */
      async startGenerationStreaming(threadId) {
        // Stop any existing stream
        this.stopStreaming(threadId);

        this.streamingThreads.add(threadId);

        try {
          const eventSource = new EventSource(
            `/llm/thread/generate?thread_id=${threadId}`
          );

          this.eventSources.set(threadId, eventSource);

          eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleStreamMessage(threadId, data);
          };

          eventSource.onerror = (error) => {
            console.error("Generation EventSource error:", error);
            this.stopStreaming(threadId);
            notification.add("Connection error during generation", {
              type: "danger",
            });
          };
        } catch (error) {
          console.error("Error starting generation streaming:", error);
          this.stopStreaming(threadId);
          notification.add("Failed to start generation", { type: "danger" });
        }
      },
    });

    return llmStore;
  },
});
