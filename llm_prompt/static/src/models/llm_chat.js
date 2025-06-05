/** @odoo-module **/

import {many} from "@mail/model/model_field";
import {registerPatch} from "@mail/model/model_core";

// Extend the thread search fields to include prompt_id
const ADDITIONAL_THREAD_FIELDS = ["prompt_id"];

registerPatch({
    name: "LLMChat",
    fields: {
        llmPrompts: many("LLMPrompt"),
    },
    recordMethods: {
        /**
         * Load prompts from the server
         */
        async loadPrompts() {
            try {
                const result = await this.messaging.rpc({
                    model: "llm.prompt",
                    method: "search_read",
                    kwargs: {
                        domain: [],
                        fields: ["name", "input_schema_json"],
                    },
                });

                // Create prompt records
                const promptData = result.map((prompt) => ({
                    id: prompt.id,
                    name: prompt.name,
                    inputSchemaJson: prompt.input_schema_json || "{}",
                }));

                this.update({llmPrompts: promptData});
            } catch (error) {
                console.error("Error loading prompts:", error);
            }
        },

        /**
         * Override to include prompt_id in the thread data mapping
         * @override
         */
        _mapThreadDataFromServer(threadData) {
            const mappedData = this._super(threadData);

            // Add prompt_id if present
            if (threadData.prompt_id) {
                mappedData.prompt_id = {
                    id: threadData.prompt_id[0],
                    name: threadData.prompt_id[1],
                };
            }

            return mappedData;
        },

        /**
         * Override to load prompts along with other resources
         * @override
         */
        async initializeLLMChat(action, initActiveId, postInitializationPromises = []) {
            // Pass our loadPrompts promise to the original method
            return this._super(action, initActiveId, [...postInitializationPromises, this.loadPrompts()]);
        },

        /**
         * Override ensureThread to load prompts as well
         * @override
         */
        async ensureThread(options) {
            // Load prompts if not already loaded
            if (!this.llmPrompts || this.llmPrompts.length === 0) {
                await this.loadPrompts();
            }

            // Call the original method
            return this._super(options);
        },

        /**
         * Override to include prompt_id in the additional fields
         * @override
         */
        async loadThreads(additionalFields = []) {
            // Add prompt_id to the additional fields
            const extendedFields = [...additionalFields, ...ADDITIONAL_THREAD_FIELDS];

            // Call the original method with the extended fields
            return this._super(extendedFields);
        },

        /**
         * Override to include prompt_id in the additional fields
         * @override
         */
        async refreshThread(threadId, additionalFields = []) {
            // Add prompt_id to the additional fields
            const extendedFields = [...additionalFields, ...ADDITIONAL_THREAD_FIELDS];

            // Call the original method with the extended fields
            return this._super(threadId, extendedFields);
        },
    },
});
