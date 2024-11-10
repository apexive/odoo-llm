/** @odoo-module **/

import { Component, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useUpdate } from "@web/core/utils/update";
import { LLMMessageList } from "../llm_message_list/llm_message_list";
import { LLMComposer } from "../llm_composer/llm_composer";
import { ThreadViewModel } from "../models";
import { ErrorBoundary } from "@web/core/errors/error_boundary";

export class LLMThreadView extends Component {
  setup() {
    super.setup();
    this.rpc = useService("rpc");
    this.notification = useService("notification");

    useUpdate({ func: () => this._update() });

    // Cleanup on destroy
    onWillDestroy(() => {
      if (this.threadView) {
        this.threadView.cleanup();
      }
    });
  }

  get threadView() {
    return this.props.record;
  }

  async _update() {
    if (!this.threadView?.thread) return;

    if (!this.threadView.hasLoadedMessages) {
      try {
        await this.threadView.thread.loadMessages();
        this.threadView.update({ hasLoadedMessages: true });
      } catch (error) {
        this.notification.notify({
          title: "Error",
          message: error.message || "Failed to load messages",
          type: "danger"
        });
      }
    }
  }

  async _onMessageSubmit(content) {
    if (!this.threadView?.thread) return;

    const thread = this.threadView.thread;
    const composer = this.threadView.composer;

    composer.disable();
    composer.clearError();

    try {
      // Send user message
      await thread.postMessage(content, "user");

      // Get and send AI response
      const response = await thread.getAIResponse(content);
      await thread.postMessage(response, "assistant");

      // Clear composer and re-enable
      composer.enable();
      composer.update({
        textInputContent: "",
        shouldFocus: true
      });
    } catch (error) {
      composer.enable();
      composer.setError(error.message || "Failed to send message");

      this.notification.notify({
        title: "Error",
        message: error.message || "Failed to send message",
        type: "danger"
      });
    }
  }

  async _onRetryMessage(messageId) {
    const message = this.threadView.thread.messages.get(messageId);
    if (!message) return;

    message.setRetrying();

    try {
      await this._onMessageSubmit(message.content);
      message.setSuccess();
    } catch (error) {
      message.setError(error.message);
    }
  }

  _onRetryLoad() {
    if (!this.threadView?.thread) return;

    this.threadView.update({
      hasError: false,
      errorMessage: ""
    });

    this.threadView.thread.loadMessages().catch(error => {
      this.threadView.update({
        hasError: true,
        errorMessage: error.message || "Failed to load messages"
      });
    });
  }
}

LLMThreadView.components = {
  LLMMessageList,
  LLMComposer,
  ErrorBoundary
};

LLMThreadView.template = "llm.ThreadView";
LLMThreadView.props = {
  record: Object,
  className: { type: String, optional: true },
};
