/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";

registerPatch({
  name: "LLMChat",
  recordMethods: {
    /**
     * Override
     * Loads LLM models from the server.
     */
    async loadLLMModels() {
      try {
        const result = await this.messaging.rpc({
          model: "llm.model",
          method: "search_read",
          kwargs: {
            domain: [],
            fields: [
              "name",
              "id",
              "provider_id",
              "default",
              "model_use",
              "input_schema",
              "output_schema",
            ],
          },
        });

        const llmModelData = result.map((model) => ({
          id: model.id,
          name: model.name,
          llmProvider: model.provider_id
              ? { id: model.provider_id[0], name: model.provider_id[1] }
              : undefined,
          default: model.default,
          modelUse: model.model_use,
          inputSchema: model.input_schema,
          outputSchema: model.output_schema,
        }));

        this.update({ llmModels: llmModelData });
      } catch (error) {
        console.error("Error loading LLM models:", error);
      }
    },

    /**
     * Get input schema and form defaults for the current thread
     * @returns {Promise<Object>} Schema and defaults information
     */
    async getThreadFormConfiguration() {
      if (!this.activeThread?.id) {
        return {
          input_schema: {},
          form_defaults: {},
          error: "No active thread"
        };
      }

      try {
        const result = await this.messaging.rpc({
          model: "llm.thread",
          method: "get_input_schema",
          args: [this.activeThread.id],
        });

        const defaults = await this.messaging.rpc({
          model: "llm.thread",
          method: "get_form_defaults",
          args: [this.activeThread.id],
        });

        return {
          input_schema: result || {},
          form_defaults: defaults || {},
        };
      } catch (error) {
        console.error("Error getting thread form configuration:", error);
        return {
          input_schema: {},
          form_defaults: {},
          error: error.message,
        };
      }
    },

    /**
     * Get model generation I/O schema by model ID (kept for compatibility)
     * @param {number} modelId - Model ID
     * @returns {Promise<Object>} Model schema information
     */
    async getModelGenerationIO(modelId) {
      try {
        const result = await this.messaging.rpc({
          model: "llm.thread",
          method: "get_model_generation_io_by_id",
          args: [modelId],
        });

        return result;
      } catch (error) {
        console.error("Error getting model generation IO:", error);
        return {
          error: error.message,
          input_schema: null,
          output_schema: null,
          model_id: modelId,
          model_name: null,
        };
      }
    },
  },
});