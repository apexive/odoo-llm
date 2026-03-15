/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, onWillDestroy, onWillStart, useState } from "@odoo/owl";
import { LLMChatContainer } from "@llm_thread/components/llm_chat_container/llm_chat_container";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * LLM Chat Client Action - Main entry point for LLM chat functionality
 *
 * v17 adaptations:
 * - Uses messagingService.isReady instead of mailStore.isReady
 */
export class LLMChatClientAction extends Component {
  static components = { LLMChatContainer };
  static props = ["*"];
  static template = "llm_thread.LLMChatClientAction";

  setup() {
    this.llmStore = useState(useService("llm.store"));
    this.mailStore = useState(useService("mail.store"));
    this.messaging = useService("mail.messaging");
    this.orm = useService("orm");
    this.notification = useService("notification");

    onWillStart(() => {
      return this.initializeLLMChat(this.props);
    });

    onWillDestroy(() => {
      this.cleanup();
    });
  }

  async initializeLLMChat(props) {
    try {
      // v17: Use messagingService.isReady + llmStore.isReady
      await Promise.all([this.messaging.isReady, this.llmStore.isReady]);

      const activeId = this.getActiveId(props);

      if (!activeId) {
        await this.loadUserThreads();
        return;
      }

      if (activeId.startsWith("llm.thread_")) {
        await this.handleThreadSelection(activeId);
      } else {
        await this.openCreateThreadForm(props);
      }
    } catch (error) {
      console.error("Error initializing LLM chat:", error);
      this.notification.add(
        _t("Could not start AI chat. Please refresh the page and try again."),
        { type: "danger" }
      );
    }
  }

  getActiveId(props) {
    return (
      props.action.context?.active_id ??
      props.action.params?.active_id ??
      props.action.context?.default_active_id
    );
  }

  async handleThreadSelection(activeId) {
    const threadId = parseInt(activeId.split("_")[1], 10);
    const existingThread = this.mailStore.Thread.get({
      model: "llm.thread",
      id: threadId,
    });

    if (!existingThread) {
      await this.loadUserThreads();
      const threadAfterLoad = this.mailStore.Thread.get({
        model: "llm.thread",
        id: threadId,
      });
      if (!threadAfterLoad) {
        this.notification.add(
          _t(
            "The requested conversation could not be found. Showing your recent conversations instead."
          ),
          { type: "warning" }
        );
        return;
      }
    }

    await this.selectLLMThread(threadId);
  }

  async selectLLMThread(threadId) {
    await this.llmStore.selectThread(threadId);
  }

  async openCreateThreadForm(props) {
    try {
      const context = props.action.context || {};
      const resModel = context.default_res_model;
      const resId = context.default_res_id;

      await this.action.doAction({
        name: "Create AI Chat",
        type: "ir.actions.act_window",
        res_model: "llm.thread",
        view_mode: "form",
        views: [[false, "form"]],
        target: "new",
        context: {
          default_model: resModel,
          default_res_id: resId,
        },
      });
    } catch (error) {
      console.error("Error opening create thread form:", error);
      this.notification.add(
        _t("Could not open the new conversation form. Please try again."),
        {
          type: "danger",
        }
      );
    }
  }

  async loadUserThreads() {
    try {
      const threads = this.llmStore.llmThreadList;

      if (threads.length > 0) {
        await this.selectLLMThread(threads[0].id);
      }
    } catch (error) {
      console.error("Error loading user threads:", error);
      this.notification.add(
        _t(
          "Could not load your conversations. Please refresh the page and try again."
        ),
        { type: "danger" }
      );
    }
  }

  cleanup() {
    this.llmStore.destroy();
  }
}

registry
  .category("actions")
  .add("llm_thread.chat_client_action", LLMChatClientAction);
