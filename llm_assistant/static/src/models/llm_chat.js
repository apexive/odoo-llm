/** @odoo-module **/

import { many } from "@mail/model/model_field";
import { clear } from "@mail/model/model_field_command";
import { registerPatch } from "@mail/model/model_core";

// Define assistant-related fields to fetch from server
const ASSISTANT_THREAD_FIELDS = ["assistant_id"];

/**
 * Patch the LLMChat model to add assistants
 */
registerPatch({
  name: "LLMChat",
  fields: {
    // Use attr instead of many for direct array access
    llmAssistants: many("LLMAssistant"),
  },
  onChanges: [
    {
      dependencies: ["activeId"],
      methodName: "onActiveIdChanged",
    },
  ],
  recordMethods: {
    /**
     * Load assistants from the server
     */
    async loadAssistants() {
      // Load assistants with their basic data and prompt_id (only actual model fields)
      const assistantResult = await this.messaging.rpc({
        model: "llm.assistant",
        method: "search_read",
        kwargs: {
          domain: [["active", "=", true]],
          fields: [
            "name",
            "default_values",
            "prompt_id",
          ],
        },
      });

      // Extract all prompt IDs to fetch their details
      const promptIds = assistantResult
          .map((assistant) => assistant.prompt_id && assistant.prompt_id[0])
          .filter((id) => id); // Filter out falsy values

      // If we have prompt IDs, fetch their details
      let promptsById = {};
      if (promptIds.length > 0) {
        const promptResult = await this.messaging.rpc({
          model: "llm.prompt",
          method: "search_read",
          kwargs: {
            domain: [["id", "in", promptIds]],
            fields: ["name", "input_schema_json"],
          },
        });

        // Create a map of prompts by ID for easy lookup
        promptsById = promptResult.reduce((acc, prompt) => {
          acc[prompt.id] = {
            id: prompt.id,
            name: prompt.name,
            inputSchemaJson: prompt.input_schema_json,
          };
          return acc;
        }, {});
      }

      // Map assistant data and include prompt details if available
      const assistantData = assistantResult.map((assistant) => {
        const data = {
          id: assistant.id,
          name: assistant.name,
          defaultValues: assistant.default_values,
          // Don't set evaluatedDefaultValues here - it will be fetched dynamically when needed
        };

        // If this assistant has a prompt, include its ID and create the relationship
        if (assistant.prompt_id && assistant.prompt_id[0]) {
          const promptId = assistant.prompt_id[0];
          data.promptId = promptId;

          // If we have the prompt details, include them
          if (promptsById[promptId]) {
            data.llmPrompt = promptsById[promptId];
          }
        }

        return data;
      });

      this.update({ llmAssistants: assistantData });
    },

    /**
     * Override ensureThread to load assistants as well
     * @override
     */
    async ensureThread(options) {
      // Load assistants if not already loaded
      if (!this.llmAssistants || this.llmAssistants.length === 0) {
        await this.loadAssistants();
      }

      // Call the original method
      return this._super(options);
    },

    /**
     * Override initializeLLMChat to include assistant loading
     * @override
     */
    async initializeLLMChat(
        action,
        initActiveId,
        postInitializationPromises = []
    ) {
      // Pass our loadAssistants promise to the original method
      return this._super(action, initActiveId, [
        ...postInitializationPromises,
        this.loadAssistants(),
      ]);
    },

    /**
     * Override loadThreads to include assistant_id field
     * @override
     */
    async loadThreads(additionalFields = []) {
      // Call the super method with our additional fields
      return this._super([...additionalFields, ...ASSISTANT_THREAD_FIELDS]);
    },

    /**
     * Override refreshThread to include assistant_id field
     * @override
     */
    async refreshThread(threadId, additionalFields = []) {
      // Call the super method with our additional fields
      return this._super(threadId, [
        ...additionalFields,
        ...ASSISTANT_THREAD_FIELDS,
      ]);
    },

    /**
     * Override _mapThreadDataFromServer to add assistant information
     * @override
     */
    _mapThreadDataFromServer(threadData) {
      // Get the base mapped data from super
      const mappedData = this._super(threadData);

      // Add assistant information if present
      if (threadData.assistant_id) {
        const assistantId = threadData.assistant_id[0];
        mappedData.llmAssistant = {
          id: assistantId,
          name: threadData.assistant_id[1],
        };

        // Only fetch thread-specific evaluated default values for the active thread
        if (this.activeId === threadData.id) {
          this._fetchAssistantValuesForThread(threadData.id, assistantId);
        }
      } else {
        // IMPORTANT: Clear the llmAssistant field when assistant_id is not present
        mappedData.llmAssistant = clear();
      }

      return mappedData;
    },

    /**
     * Handle active thread changes
     */
    onActiveIdChanged() {
      if (!this.activeId) {
        return;
      }
      const [model, id] =
          typeof this.activeId === "number"
              ? ["llm.thread", this.activeId]
              : this.activeId.split("_");
      // Get the active thread
      const activeThread = this.messaging.models.Thread.findFromIdentifyingData(
          { id: Number(id), model }
      );
      if (!activeThread || !activeThread.llmAssistant) {
        return;
      }

      // Fetch thread-specific evaluated default values for the active thread's assistant
      this._fetchAssistantValuesForThread(
          activeThread.id,
          activeThread.llmAssistant.id
      );
    },

    /**
     * Fetch thread-specific evaluated default values for an assistant
     * @param {Number} threadId - ID of the thread
     * @param {Number} assistantId - ID of the assistant
     * @private
     */
    async _fetchAssistantValuesForThread(threadId, assistantId) {
      try {
        const result = await this.messaging.rpc({
          route: "/llm/thread/get_assistant_values",
          params: {
            thread_id: threadId,
            assistant_id: assistantId,
          },
        });

        if (result.success) {
          // Find the thread and update its assistant with the evaluated values
          const thread = this.messaging.models.Thread.findFromIdentifyingData({
            id: threadId,
            model: "llm.thread",
          });
          if (thread) {
            // Find the assistant in our registry
            const assistant = this.llmAssistants.find(
                (a) => a.id === assistantId
            );
            if (assistant) {
              // Update the assistant with thread-specific evaluated values
              if (result.evaluated_default_values) {
                assistant.update({
                  defaultValues: result.default_values,
                  evaluatedDefaultValues: result.evaluated_default_values,
                });
              } else {
                console.log("cleaning default values");
                // Clean up default values when there are no evaluated default values
                assistant.update({
                  defaultValues: clear(),
                  evaluatedDefaultValues: clear(),
                });
              }

              // If we have prompt data, update or create the prompt relationship
              if (result.prompt) {
                const promptData = result.prompt;
                const prompt =
                    this.messaging.models.LLMPrompt.findFromIdentifyingData({
                      id: promptData.id,
                    });

                if (prompt) {
                  // Update existing prompt
                  prompt.update({
                    name: promptData.name,
                    inputSchemaJson: promptData.input_schema_json,
                  });
                } else {
                  // Create new prompt record
                  this.messaging.models.LLMPrompt.insert({
                    id: promptData.id,
                    name: promptData.name,
                    inputSchemaJson: promptData.input_schema_json,
                  });
                }

                // Update assistant with prompt relationship
                assistant.update({
                  promptId: promptData.id,
                  llmPrompt: { id: promptData.id },
                });
              }
            }
          }
        } else {
          console.error("Error fetching assistant values:", result.error);
        }
      } catch (error) {
        console.error("Error in _fetchAssistantValuesForThread:", error);
      }
    },
  },
});
