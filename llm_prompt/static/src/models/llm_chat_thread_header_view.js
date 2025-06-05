/** @odoo-module **/

import {attr, one} from "@mail/model/model_field";
import {clear} from "@mail/model/model_field_command";
import {registerPatch} from "@mail/model/model_core";

registerPatch({
    name: "LLMChatThreadHeaderView",
    fields: {
        /**
         * Selected prompt ID
         */
        selectedPromptId: attr(),

        /**
         * Selected prompt record
         */
        selectedPrompt: one("LLMPrompt", {
            compute() {
                if (!this.selectedPromptId) {
                    return clear();
                }
                // Search within the collection of LLMPrompt records
                const prompts = this.threadView?.thread?.llmChat?.llmPrompts;
                if (!prompts || !Array.isArray(prompts)) {
                    return clear();
                }
                return (
                    prompts.find((promptRecord) => promptRecord && promptRecord.id === this.selectedPromptId) ||
                    clear()
                );
            },
        }),
    },
    recordMethods: {
        /**
         * Initialize or reset state based on current thread
         * @override
         * @private
         */
        _initializeState() {
            this._super();
            const currentThread = this.threadView?.thread;
            if (!currentThread) {
                this.update({
                    selectedPromptId: clear(),
                });
                return;
            }

            this.update({
                selectedPromptId: currentThread.prompt_id?.id || clear(),
            });
        },

        /**
         * Save the selected prompt to the thread
         * @param {Number|Boolean} promptId - The ID of the prompt to set, or false to clear
         */
        async saveSelectedPrompt(promptId) {
            if (promptId === this.selectedPromptId) {
                return;
            }

            // Update the local state immediately for responsive UI
            this.update({
                selectedPromptId: promptId || clear(),
            });

            try {
                const result = await this.messaging.rpc({
                    route: "/llm/thread/set_prompt",
                    params: {
                        thread_id: this.threadView.thread.id,
                        prompt_id: promptId || false,
                    },
                });

                if (!result) {
                    // If the server call was not successful, throw an error
                    throw new Error("Failed to update prompt");
                }

                // Refresh the thread to get updated data
                await this.threadView.thread.llmChat.refreshThread(this.threadView.thread.id, ["prompt_id"]);
            } catch (error) {
                console.error("Failed to update thread prompt:", error);

                // Revert the local state if the server call failed
                this.update({
                    selectedPromptId: this.threadView.thread.prompt_id?.id || clear(),
                });

                this.messaging.notify({
                    type: "danger",
                    message: this.env._t("Failed to update prompt. Please try again."),
                });
            }
        },
    },
});
