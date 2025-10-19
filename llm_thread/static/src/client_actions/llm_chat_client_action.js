/** @odoo-module **/

import { Component, useState, onWillStart, onWillDestroy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { LLMChatContainer } from "@llm_thread/components/llm_chat_container/llm_chat_container";

/**
 * LLM Chat Client Action - Main entry point for LLM chat functionality
 * Follows Odoo 17.0 client action pattern similar to DiscussClientAction
 */
export class LLMChatClientAction extends Component {
  static components = { LLMChatContainer };
  static props = ["*"];
  static template = "llm_thread.LLMChatClientAction";

  setup() {
    this.llmStore = useService("llm.store");
    this.mailStore = useService("mail.store");
    this.messaging = useService("mail.messaging");
    this.orm = useService("orm");
    this.notification = useService("notification");
    this.action = useService("action");

    onWillStart(() => {
      return this.initializeLLMChat(this.props);
    });

    onWillDestroy(() => {
      this.cleanup();
    });
  }

  /**
   * Initialize LLM chat based on action context
   * Similar to how DiscussClientAction handles thread restoration
   */
  async initializeLLMChat(props) {
    try {
      // Wait for both messaging and llmStore to be ready
      // messaging.isReady ensures threads are loaded via init_messaging
      // llmStore.isReady ensures providers, models, tools are loaded
      await Promise.all([this.messaging.isReady, this.llmStore.isReady]);

      const activeId = this.getActiveId(props);

      if (activeId) {
        if (activeId.startsWith("llm.thread_")) {
          // Direct LLM thread reference
          const threadId = parseInt(activeId.split("_")[1]);

          // Check if thread exists in loaded threads, if not load user threads first
          const existingThread = this.mailStore.Thread.get({
            model: "llm.thread",
            id: threadId,
          });
          if (!existingThread) {
            // Thread not loaded in init_messaging, might be from another user or not accessible
            // Load user threads first, then try to select the specific one
            await this.loadUserThreads();

            // Try again after loading
            const threadAfterLoad = this.mailStore.Thread.get({
              model: "llm.thread",
              id: threadId,
            });
            if (threadAfterLoad) {
              await this.selectLLMThread(threadId);
            } else {
              // Thread not found, fall back to first available thread
              this.notification.add(
                "Requested thread not found, showing recent threads",
                { type: "warning" }
              );
              await this.loadUserThreads();
            }
          } else {
            // Thread exists, select it
            await this.selectLLMThread(threadId);
          }
        } else {
          // Open form to create new LLM thread for the referenced record
          await this.openCreateThreadForm(props);
        }
      } else {
        // No specific context, load user's recent threads
        await this.loadUserThreads();
      }
    } catch (error) {
      console.error("Error initializing LLM chat:", error);
      // Log detailed error information
      console.error("Error details:", {
        message: error.message,
        stack: error.stack,
        error: error,
      });
      this.notification.add(
        `Failed to initialize AI chat: ${error.message || "Unknown error"}`,
        {
          type: "danger",
          sticky: true, // Make notification persistent
        }
      );
    }
  }

  /**
   * Get active ID from action context, similar to DiscussClientAction
   */
  getActiveId(props) {
    return (
      props.action.context?.active_id ??
      props.action.params?.active_id ??
      props.action.context?.default_active_id
    );
  }

  /**
   * Select an existing LLM thread - delegates to service
   */
  async selectLLMThread(threadId) {
    // Use the consolidated service method
    await this.llmStore.selectThread(threadId);
  }

  /**
   * Open llm.thread form to create new thread for a specific record
   */
  async openCreateThreadForm(props) {
    try {
      const context = props.action.context || {};
      const resModel = context.default_res_model;
      const resId = context.default_res_id;
      const name = context.default_name || `AI Chat - ${resModel} #${resId}`;

      await this.action.doAction({
        name: "Create AI Chat",
        type: "ir.actions.act_window",
        res_model: "llm.thread",
        view_mode: "form",
        views: [[false, "form"]],
        target: "new",
        context: {
          default_name: name,
          default_model: resModel,
          default_res_id: resId,
        },
      });
    } catch (error) {
      console.error("Error opening create thread form:", error);
      this.notification.add("Failed to open chat creation form", {
        type: "danger",
      });
    }
  }

  /**
   * Load user's existing LLM threads
   */
  async loadUserThreads() {
    try {
      // Threads are automatically loaded via init_messaging
      // Just get the most recent one from mailStore
      const threads = this.llmStore.llmThreadList;

      console.log("this", this);
      console.log("this.llmStore", this.llmStore);
      console.log("threads", threads);

      if (threads.length > 0) {
        await this.selectLLMThread(threads[0].id);
      }
      // No auto-creation - let user create threads via form
    } catch (error) {
      console.error("Error loading user threads:", error);
      // Log detailed error information
      console.error("Error details:", {
        message: error.message,
        stack: error.stack,
        error: error,
      });
      this.notification.add(
        `Failed to load chat threads: ${error.message || "Unknown error"}`,
        {
          type: "danger",
          sticky: true, // Make notification persistent
        }
      );
    }
  }

  /**
   * Cleanup when component is destroyed
   */
  cleanup() {
    // Stop any streaming
    this.llmStore.destroy();
  }
}

// Register client action
registry
  .category("actions")
  .add("llm_thread.chat_client_action", LLMChatClientAction);
