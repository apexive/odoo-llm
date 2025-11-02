/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Thread } from "@mail/core/common/thread";
import { Composer } from "@mail/core/common/composer";
import { LLMThreadHeader } from "../llm_thread_header/llm_thread_header";

/**
 * LLM Chat Container - Main container for LLM chat UI
 * Uses existing mail Thread and Composer components with LLM patches
 */
export class LLMChatContainer extends Component {
  static components = { Thread, Composer, LLMThreadHeader };
  static template = "llm_thread.LLMChatContainer";

  setup() {
    this.llmStore = useState(useService("llm.store"));
    this.mailStore = useState(useService("mail.store"));
    this.action = useService("action");

    // No need for local thread tracking - use mail.store.discuss.thread
  }

  /**
   * Get the active thread from standard mail.store.discuss
   */
  get activeThread() {
    const thread = this.mailStore.discuss?.thread;
    return thread;
  }

  /**
   * Check if we have an active LLM thread
   */
  get hasActiveThread() {
    return this.activeThread?.model === "llm.thread";
  }

  /**
   * Get composer for the active thread
   */
  get threadComposer() {
    return this.activeThread?.composer;
  }

  /**
   * Check if this thread is currently streaming
   */
  get isStreaming() {
    return this.llmStore.getStreamingStatus();
  }

  /**
   * Select thread - delegates to LLM store service
   */
  async selectThread(threadId) {
    await this.llmStore.selectThread(threadId);
  }

  /**
   * Check if a thread is currently streaming
   */
  isStreamingThread(threadId) {
    return this.llmStore.isStreamingThread(threadId);
  }

  /**
   * Format date for display
   */
  formatDate(dateString) {
    if (!dateString) return "";
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffHours < 1) {
      return "Just now";
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else if (diffDays < 7) {
      return `${diffDays}d ago`;
    } else {
      return date.toLocaleDateString();
    }
  }

  /**
   * Create new thread - delegates to llm store service
   */
  async createNewThread() {
    await this.llmStore.createNewThread();
  }
}

LLMChatContainer.props = {
  "*": true, // Accept any props (like updateActionState)
};
