/** @odoo-module **/

import { Component, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { LLMMessageList } from "../llm_message_list/llm_message_list";
import { LLMComposer } from "../llm_composer/llm_composer";

/**
 * Stream response handler
 */
class StreamHandler {
  constructor(onChunk, onComplete, onError) {
    this.buffer = "";
    this.onChunk = onChunk;
    this.onComplete = onComplete;
    this.onError = onError;
  }

  /**
   * Process a chunk from the stream
   * @param {string} chunk Raw chunk data
   */
  processChunk(chunk) {
    try {
      // Add chunk to buffer
      this.buffer += chunk;

      // Process complete messages
      const lines = this.buffer.split("\n");
      this.buffer = lines.pop() || ""; // Keep incomplete line in buffer

      for (const line of lines) {
        if (!line.trim()) continue;
        const data = JSON.parse(line);
        this.onChunk(data);
      }
    } catch (error) {
      this.onError(error);
    }
  }

  /**
   * Complete the stream
   */
  complete() {
    // Process any remaining buffer
    if (this.buffer.trim()) {
      try {
        const data = JSON.parse(this.buffer);
        this.onChunk(data);
      } catch (error) {
        this.onError(error);
      }
    }
    this.onComplete();
  }
}

export class LLMThreadView extends Component {
  setup() {
    // Services
    this.rpc = useService("rpc");
    this.notification = useService("notification");
    this.orm = useService("orm");
    this.action = useService("action");

    // State management
    this.currentResponse = null;
    this.isLoadingInitial = true;

    // Lifecycle hooks
    onMounted(() => this._mounted());
    onWillUnmount(() => this._cleanup());
  }

  /**
   * @returns {Object} The thread view record from props
   */
  get threadView() {
    return this.props.record;
  }

  /**
   * @returns {Object} The thread record
   */
  get thread() {
    return this.threadView.thread;
  }

  /**
   * Component mounted hook
   * @private
   */
  async _mounted() {
    if (!this.thread) return;

    try {
      await this._loadMessages();
    } catch (error) {
      this._handleError(error);
    } finally {
      this.isLoadingInitial = false;
    }
  }

  /**
   * Clean up resources
   * @private
   */
  _cleanup() {
    if (this.currentResponse?.signal?.abort) {
      this.currentResponse.signal.abort();
    }
  }

  /**
   * Load thread messages
   * @private
   */
  async _loadMessages() {
    if (!this.thread.id) return;

    try {
      const result = await this.rpc('/llm/thread/data', {
        thread_id: this.thread.id,
      });

      // Update thread with loaded data
      this.thread.update({
        messages: result.messages,
        hasError: false,
        errorMessage: null,
      });

    } catch (error) {
      throw new Error(this.env._t("Failed to load messages"));
    }
  }

  /**
   * Handle message submission
   * @param {string} content Message content
   * @private
   */
  async _onMessageSubmit(content) {
    if (!content.trim()) return;

    const composer = this.threadView.composer;
    composer.disable();

    try {
      // Add user message
      await this._addMessage(content, 'user');

      // Get AI response
      await this._getAIResponse(content);

      composer.enable();
      composer.update({
        content: "",
        shouldFocus: true,
      });

    } catch (error) {
      this._handleError(error);
      composer.enable();
    }
  }

  /**
   * Add a message to the thread
   * @param {string} content Message content
   * @param {string} role Message role
   * @private
   */
  async _addMessage(content, role = 'user') {
    try {
      await this.orm.call('llm.thread', 'send_message', [[this.thread.id], {
        content,
        role,
      }]);

      // Reload messages to get the new message
      await this._loadMessages();

    } catch (error) {
      throw new Error(this.env._t("Failed to send message"));
    }
  }

  /**
   * Get AI response using streaming
   * @param {string} content User message content
   * @private
   */
  async _getAIResponse(content) {
    const controller = new AbortController();
    this.currentResponse = controller;

    try {
      // Create temporary message for streaming
      const tempMessage = this.thread.messaging.models.LLMMessage.insert({
        content: '',
        role: 'assistant',
        status: 'sending',
        thread: this.thread,
      });

      // Setup stream handler
      const streamHandler = new StreamHandler(
          // Chunk handler
          (data) => {
            if (data.content) {
              tempMessage.update({
                content: tempMessage.content + data.content,
              });
            }
          },
          // Complete handler
          () => {
            tempMessage.update({ status: 'sent' });
            this.currentResponse = null;
          },
          // Error handler
          (error) => {
            tempMessage.update({
              status: 'error',
              error: error.message || this.env._t("Failed to process response"),
            });
            this.currentResponse = null;
          }
      );

      // Start streaming
      const response = await this.rpc('/llm/thread/stream_response', {
        thread_id: this.thread.id,
        content,
      }, {
        signal: controller.signal,
      });

      // Process stream response
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        streamHandler.processChunk(chunk);
      }

      streamHandler.complete();

    } catch (error) {
      if (error.name === 'AbortError') return;
      throw new Error(this.env._t("Failed to get AI response"));
    }
  }

  /**
   * Handle error display
   * @param {Error} error Error object
   * @private
   */
  _handleError(error) {
    this.notification.add(
        error.message || this.env._t("An error occurred"),
        { type: 'danger' }
    );
  }

  /**
   * Handle message retry
   * @param {Object} message Message to retry
   * @private
   */
  async _onMessageRetry(message) {
    if (message.role !== 'user') return;

    message.update({ status: 'sending' });

    try {
      await this._onMessageSubmit(message.content);
      message.update({ status: 'sent' });
    } catch (error) {
      message.update({
        status: 'error',
        error: error.message,
      });
    }
  }

  /**
   * Handle file paste in composer
   * @param {File[]} files Pasted files
   * @private
   */
  async _onFilesPasted(files) {
    // Handle different file types
    for (const file of files) {
      if (file.type.startsWith('image/')) {
        await this._handleImagePaste(file);
      } else {
        this.notification.add(
            this.env._t("Only image files are supported"),
            { type: 'warning' }
        );
      }
    }
  }

  /**
   * Handle pasted image
   * @param {File} file Image file
   * @private
   */
  async _handleImagePaste(file) {
    try {
      // Convert image to base64
      const reader = new FileReader();
      const base64 = await new Promise((resolve, reject) => {
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      // Send message with image
      await this._addMessage(base64, 'user');
      await this._getAIResponse('[Image Analysis Request]');

    } catch (error) {
      this._handleError(new Error(this.env._t("Failed to process image")));
    }
  }
}

LLMThreadView.components = {
  LLMMessageList,
  LLMComposer,
};

LLMThreadView.template = "llm.ThreadView";

LLMThreadView.props = {
  record: {
    type: Object,
    required: true,
  },
  className: {
    type: String,
    optional: true,
  }
};

// Register the component
registry.category("components").add("LLMThreadView", LLMThreadView);
