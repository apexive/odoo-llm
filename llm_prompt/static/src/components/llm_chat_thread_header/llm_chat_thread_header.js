/** @odoo-module **/

import {LLMChatThreadHeader} from "@llm_thread/components/llm_chat_thread_header/llm_chat_thread_header";
import {patch} from "@web/core/utils/patch";

patch(LLMChatThreadHeader.prototype, "llm_prompt.llm_prompt_dropdown_patch", {
    /**
     * Get all available prompts
     */
    get llmPrompts() {
        // Make sure we have a valid llmChat reference
        if (!this.llmChat) {
            return [];
        }

        // Return the prompts array
        return this.llmChat.llmPrompts || [];
    },

    /**
     * Handle prompt selection
     * @param {Object} prompt - The selected prompt
     */
    onSelectPrompt(prompt) {
        this.llmChatThreadHeaderView.saveSelectedPrompt(prompt.id);
    },

    /**
     * Clear the selected prompt
     */
    onClearPrompt() {
        this.llmChatThreadHeaderView.saveSelectedPrompt(false);
    },
});
