/** @odoo-module **/

import { Component, useState, useRef, onWillDestroy, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { LLMMessageList } from "../llm_message_list/llm_message_list";
import { LLMComposer } from "../llm_composer/llm_composer";

/**
 * Thread view component for LLM chat interface
 */
export class LLMThreadView extends Component {
  setup() {
    // Services
    this.rpc = useService("rpc");
    this.notification = useService("notification");
    this.orm = useService("orm");

    // Refs
    this.containerRef = useRef("container");

    // State
    this.state = useState({
      messages: [],
      isLoadingInitial: true,
      isLoadingMore: false,
      hasError: false,
      errorMessage: null,
      currentResponse: null
    });

    // Composer state
    this.composerState = useState({
      content: "",
      isDisabled: false,
      placeholder: this.env._t("Type a message..."),
      error: null
    });

    // Get record ID from props
    this.threadId = this.props.record.data.id;

    // Setup lifecycle hooks
    onMounted(() => this._loadMessages());
    onWillDestroy(() => this._cleanup());
  }

  /**
   * Load messages from server
   * @private
   */
  async _loadMessages() {
    if (this.state.isLoadingMore || !this.threadId) return;

    try {
      this.state.isLoadingMore = true;
      this.state.hasError = false;

      const data = await this.rpc("/llm/thread/data", {
        thread_id: this.threadId
      });

      this.state.messages = data.messages || [];
      this.thread = data;

    } catch (error) {
      this.state.hasError = true;
      this.state.errorMessage = error.message || "Failed to load messages";
      this.notification.add(this.state.errorMessage, { type: "danger" });
    } finally {
      this.state.isLoadingInitial = false;
      this.state.isLoadingMore = false;
    }
  }

  /**
   * Handle message submission
   * @param {string} content Message content
   * @private
   */
  async _onMessageSubmit(content) {
    if (!content.trim() || !this.threadId) return;

    // Disable composer while processing
    this.composerState.isDisabled = true;

    try {
      await this.rpc("/llm/thread/post_message", {
        thread_id: this.threadId,
        content,
        role: "user"
      });

      // Reload messages to get the response
      await this._loadMessages();

    } catch (error) {
      this.notification.add(
          error.message || "Failed to send message",
          { type: "danger" }
      );
      this.composerState.error = error.message || "Failed to send message";
    } finally {
      this.composerState.isDisabled = false;
    }
  }

  /**
   * Handle message retry
   * @param {Object} message Message to retry
   * @private
   */
  async _onMessageRetry(message) {
    const index = this.state.messages.indexOf(message);
    if (index === -1) return;

    // Remove failed message and try again
    this.state.messages.splice(index, 1);
    await this._onMessageSubmit(message.content);
  }

  /**
   * Cleanup resources
   * @private
   */
  _cleanup() {
    // Add any cleanup needed
  }
}

LLMThreadView.template = "llm.ThreadView";
LLMThreadView.components = { LLMMessageList, LLMComposer };

// Define props including standard widget props
LLMThreadView.props = {
  ...standardWidgetProps,
  className: { type: String, optional: true }
};

// Register as both a regular component and a form widget
registry.category("components").add("LLMThreadView", LLMThreadView);
registry.category("view_widgets").add("llm_thread_view", LLMThreadView);
