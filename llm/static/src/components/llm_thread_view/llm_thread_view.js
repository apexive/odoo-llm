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
   * Read stream response data
   * @param {ReadableStream} stream Response stream
   * @private
   */
  async _readStream(stream) {
    const reader = stream.getReader();
    let content = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Parse and accumulate streamed content
        const text = new TextDecoder().decode(value);
        const lines = text.split("\n").filter((line) => line.trim());

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(5);
            if (data === "[DONE]") continue;
            try {
              const parsed = JSON.parse(data);
              content += parsed;

              // Update streamed message in state
              this.state.streamedMessage = {
                id: "streaming",
                role: "assistant",
                content,
                timestamp: new Date().toISOString(),
                author: this.state.thread?.model?.name || "Assistant",
                isStreaming: true,
              };
            } catch (e) {
              console.error("Error parsing stream data:", e);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
      // Clear streaming state and reload messages
      this.state.isStreaming = false;
      this.state.streamedMessage = null;
      await this._loadMessages();
    }
  }

  /**
   * Handle message submission with streaming support
   * @param {string} content Message content
   * @private
   */
  async _onMessageSubmit(content) {
    if (!content.trim() || !this.threadId) return;

    // Disable composer while processing
    this.state.composerDisabled = true;

    try {
      // Start streaming state
      this.state.isStreaming = true;
      this.state.streamedMessage = null;

      const response = await fetch(`/llm/thread/post_message`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          method: "call",
          params: {
            thread_id: this.threadId,
            content,
            role: "user",
            stream: true,
          },
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (response.headers.get("content-type").includes("text/event-stream")) {
        await this._readStream(response.body);
      } else {
        // Handle non-streaming response
        const result = await response.json();
        if (result.error) {
          throw new Error(result.error.message || "Unknown error");
        }
        await this._loadMessages();
      }
    } catch (error) {
      this.notification.add(error.message || "Failed to send message", {
        type: "danger",
      });
    } finally {
      this.state.composerDisabled = false;
      this.state.isStreaming = false;
    }
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
        // Add scroll position update logic
      },
    };
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
        role: "user",
      });

      // Reload messages to get the response
      await this._loadMessages();
    } catch (error) {
      this.notification.add(error.message || "Failed to send message", {
        type: "danger",
      });
    } finally {
      this.state.composerDisabled = false;
    }
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
  className: { type: String, optional: true },
};

// Register as both a regular component and a form widget
registry.category("components").add("LLMThreadView", LLMThreadView);
registry.category("view_widgets").add("llm_thread_view", LLMThreadView);
