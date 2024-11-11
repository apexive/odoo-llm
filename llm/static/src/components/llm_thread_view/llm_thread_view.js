/** @odoo-module **/

import {
  Component,
  useState,
  useRef,
  onWillDestroy,
  onMounted,
} from "@odoo/owl";
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
    this.messaging = useService("messaging");

    // Refs
    this.containerRef = useRef("container");
    this.eventSource = null;

    // State
    this.state = useState({
      isLoadingInitial: true,
      isLoadingMore: false,
      hasError: false,
      errorMessage: null,
      thread: null,
      composerDisabled: false,
      isStreaming: false,
      streamedMessage: null,
      messages: [],
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
   * Get CSRF token from the page
   * @returns {string} CSRF token
   * @private
   */
  _getCSRFToken() {
    const tokenEl = document.querySelector('meta[name="csrf-token"]');
    return tokenEl ? tokenEl.getAttribute("content") : "";
  }

  /**
   * Handle message submission with streaming response
   * @param {string} content Message content
   * @private
   */
  async _onMessageSubmit(content) {
    if (!content.trim() || !this.threadId) return;

    // Disable composer while processing
    this.state.composerDisabled = true;

    // Clean up any existing EventSource
    this._closeEventSource();

    try {
      // Post user message
      await this.rpc("/llm/thread/post_message", {
        thread_id: this.threadId,
        content,
        role: "user",
      });

      // Reload to show user message
      await this._loadMessages();

      // Start streaming
      this.state.isStreaming = true;
      this.state.streamedMessage = null;

      // Get CSRF token
      const token = this._getCSRFToken();

      // Create new EventSource
      this.eventSource = new EventSource(
        `/llm/thread/stream_response?thread_id=${this.threadId}&csrf_token=${token}`
      );

      let accumulatedContent = "";

      await new Promise((resolve, reject) => {
        if (!this.eventSource) {
          reject(new Error("EventSource not initialized"));
          return;
        }

        this.eventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            switch (data.type) {
              case "start":
                // Stream started
                break;

              case "content":
                if (this.isDestroyed()) {
                  this._closeEventSource();
                  resolve();
                  return;
                }

                // Accumulate content
                accumulatedContent += data.content;

                // Update streaming message
                this.state.streamedMessage = {
                  id: "streaming",
                  role: "assistant",
                  content: accumulatedContent,
                  timestamp: new Date().toISOString(),
                  author: this.state.thread?.model?.name || "Assistant",
                  isStreaming: true,
                };
                this.render();
                break;

              case "error":
                this._closeEventSource();
                reject(new Error(data.error));
                break;

              case "end":
                this._closeEventSource();
                resolve();
                break;
            }
          } catch (error) {
            this._closeEventSource();
            reject(error);
          }
        };

        this.eventSource.onerror = (error) => {
          this._closeEventSource();
          reject(new Error("Stream connection failed"));
        };
      });
    } catch (error) {
      this.notification.add(error.message || "Failed to send message", {
        type: "danger",
      });
    } finally {
      // Clean up
      this.state.composerDisabled = false;
      this.state.isStreaming = false;
      this.state.streamedMessage = null;
      this._closeEventSource();

      // Final reload to get complete conversation
      await this._loadMessages();
    }
  }

  /**
   * Close and cleanup EventSource
   * @private
   */
  _closeEventSource() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  /**
   * Check if component is destroyed
   * @returns {boolean}
   * @private
   */
  isDestroyed() {
    return !this.containerRef.el || !this.containerRef.el.isConnected;
  }

  /**
   * Get message list record for the template
   * @returns {Object} Message list record
   */
  get messageListRecord() {
    if (!this.state.thread?.messages) {
      return null;
    }

    const messages = [...this.state.thread.messages];
    if (this.state.streamedMessage) {
      messages.push(this.state.streamedMessage);
    }

    return {
      messages,
      isLoadingMore: this.state.isLoadingMore,
      hasMoreMessages: false,
      isAtBottom: true,
      updateScroll: (position, isAtBottom) => {
        // Add scroll position update logic if needed
      },
    };
  }

  /**
   * Get thread ID from props or params
   * @returns {number|null}
   * @private
   */
  _getThreadId() {
    if (this.props.record?.data?.id) {
      return this.props.record.data.id;
    }
    if (this.props.threadId) {
      return this.props.threadId;
    }
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
        thread_id: this.threadId,
      });

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
   * Cleanup resources
   * @private
   */
  _cleanup() {
    this._closeEventSource();
  }
}

LLMThreadView.template = "llm.ThreadView";
LLMThreadView.components = { LLMMessageList, LLMComposer };

// Define props including standard widget props
LLMThreadView.props = {
  ...standardWidgetProps,
  record: { type: Object, optional: true },
  threadId: { type: Number, optional: true },
  className: { type: String, optional: true },
};

// Register as both a regular component and a form widget
registry.category("components").add("LLMThreadView", LLMThreadView);
registry.category("view_widgets").add("llm_thread_view", LLMThreadView);
