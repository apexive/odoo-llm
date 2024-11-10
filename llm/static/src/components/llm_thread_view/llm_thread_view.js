/** @odoo-module **/

import { Component, useState, useRef, onWillDestroy, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { LLMMessageList } from "../llm_message_list/llm_message_list";
import { LLMComposer } from "../llm_composer/llm_composer";

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
      currentResponse: null,
      thread: null,
      composerDisabled: false
    });

    // Get thread ID from props or params
    this.threadId = this._getThreadId();

    // Setup lifecycle hooks
    if (this.threadId) {
      onMounted(() => this._loadMessages());
    } else {
      this.state.isLoadingInitial = false;
      this.state.hasError = true;
      this.state.errorMessage = "No thread ID provided";
    }

    onWillDestroy(() => this._cleanup());
  }

  /**
   * Get thread ID from props or params
   * @returns {number|null}
   * @private
   */
  _getThreadId() {
    // Try to get ID from record props
    if (this.props.record?.data?.id) {
      return this.props.record.data.id;
    }

    // Try to get ID from direct props
    if (this.props.threadId) {
      return this.props.threadId;
    }

    // Try to get ID from action params
    if (this.env.action?.params?.thread_id) {
      return this.env.action.params.thread_id;
    }

    return null;
  }

  /**
   * Load messages from server
   * @private
   */
  async _loadMessages() {
    if (!this.threadId || this.state.isLoadingMore) return;

    try {
      this.state.isLoadingMore = true;
      this.state.hasError = false;

      const data = await this.rpc("/llm/thread/data", {
        thread_id: this.threadId
      });

      this.state.messages = data.messages || [];
      this.state.thread = data;

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
    this.state.composerDisabled = true;

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
    } finally {
      this.state.composerDisabled = false;
    }
  }

  /**
   * Handle message retry
   * @param {Object} message Message to retry
   * @private
   */
  async _onMessageRetry(message) {
    if (!message || !this.threadId) return;

    // Remove failed message and try again
    this.state.messages = this.state.messages.filter(m => m.id !== message.id);
    await this._onMessageSubmit(message.content);
  }

  /**
   * Cleanup resources
   * @private
   */
  _cleanup() {
    // Clean up any resources or event listeners if needed
  }
}

LLMThreadView.template = "llm.ThreadView";
LLMThreadView.components = { LLMMessageList, LLMComposer };

// Define props including standard widget props
LLMThreadView.props = {
  ...standardWidgetProps,
  record: { type: Object, optional: true },
  threadId: { type: Number, optional: true },
  className: { type: String, optional: true }
};

// Register as both a regular component and a form widget
registry.category("components").add("LLMThreadView", LLMThreadView);
registry.category("view_widgets").add("llm_thread_view", LLMThreadView);
