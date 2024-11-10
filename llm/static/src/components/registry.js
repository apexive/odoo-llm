/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

// Import components
import { LLMMessage } from "./llm_message/llm_message";
import { LLMMessageList } from "./llm_message_list/llm_message_list";
import { LLMComposer } from "./llm_composer/llm_composer";
import { LLMThreadView } from "./llm_thread_view/llm_thread_view";
import { LLMChatDialog, LLMChatDialogAction } from "./llm_chat_dialog/llm_chat_dialog";

// Register Components
const componentRegistry = registry.category("components");
componentRegistry.add("LLMMessage", LLMMessage);
componentRegistry.add("LLMMessageList", LLMMessageList);
componentRegistry.add("LLMComposer", LLMComposer);
componentRegistry.add("LLMThreadView", LLMThreadView);
componentRegistry.add("LLMChatDialog", LLMChatDialog);

// Register Dialog Action
registry.category("actions").add("llm_chat_dialog", LLMChatDialogAction);

// Register Widget
registry.category("view_widgets").add("llm_thread_view", {
    component: LLMThreadView,
    extractProps: ({ attrs, context }) => ({
        ...standardWidgetProps(attrs, context),
        readonly: attrs.readonly === "true",
    }),
});

// Register Template Views
registry.category("views").add("llm_thread_view", {
    type: "llm_thread_view",
    component: LLMThreadView,
    buttonTemplate: "llm.ThreadView.Buttons",
});

