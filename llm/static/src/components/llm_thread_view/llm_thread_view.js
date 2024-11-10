/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useComponentToModel } from "@mail/component_hooks/use_component_to_model";
import { useUpdate } from "@mail/component_hooks/use_update";

export class LLMThreadView extends Component {
  setup() {
    super.setup();
    useComponentToModel({ fieldName: "component" });
    useUpdate({ func: () => this._update() });
  }

  /**
   * @returns {LLMThreadView}
   */
  get threadView() {
    return this.props.record;
  }

  /**
   * Handler for new messages
   * @private
   */
  _update() {
    if (!this.threadView || !this.threadView.thread) {
      return;
    }

    // Auto-load messages if needed
    if (!this.threadView.hasLoadedMessages) {
      this.threadView.thread.loadMessages();
      this.threadView.update({ hasLoadedMessages: true });
    }
  }

  /**
   * Handler for message submission
   * @param {String} content
   */
  async _onMessageSubmit(content) {
    if (!this.threadView?.thread) {
      return;
    }

    const thread = this.threadView.thread;

    // Update composer state
    this.threadView.composer.update({
      isDisabled: true,
      textInputContent: "",
    });

    try {
      // Add user message
      await thread.postMessage({
        content: content,
        role: "user",
      });

      // Start AI response
      const response = await thread.getAIResponse(content);

      // Add AI response
      await thread.postMessage({
        content: response,
        role: "assistant",
      });
    } catch (error) {
      this.threadView.update({
        hasError: true,
        errorMessage: error.message || "Failed to get response",
      });
    } finally {
      // Re-enable composer
      this.threadView.composer.update({
        isDisabled: false,
        shouldFocus: true,
      });
    }
  }

  /**
   * Retry loading messages
   */
  _onRetryLoad() {
    if (!this.threadView?.thread) {
      return;
    }
    this.threadView.update({ hasError: false });
    this.threadView.thread.loadMessages();
  }
}

Object.assign(LLMThreadView, {
  components: {
    LLMMessageList: () =>
      import("@llm/components/llm_message_list/llm_message_list.js"),
    LLMComposer: () => import("@llm/components/llm_composer/llm_composer.js"),
  },
  props: { record: Object },
  template: "llm.ThreadView",
});
