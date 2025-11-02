/** @odoo-module **/

import { LLMChatContainer } from "@llm_thread/components/llm_chat_container/llm_chat_container";
import { registry } from "@web/core/registry";

// Register the client action
registry
  .category("actions")
  .add("llm_thread.chat_client_action", LLMChatContainer);
