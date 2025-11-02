/** @odoo-module **/

import { registerMessagingComponent } from "@mail/utils/messaging_component";
const { Component } = owl;
export class LLMChat extends Component {
  // --------------------------------------------------------------------------
  // Public
  // --------------------------------------------------------------------------

  /**
   * @returns {LLMChatView}
   */
  get llmChatView() {
    return this.props.record;
  }
}

Object.assign(LLMChat, {
  props: { record: Object },
  template: "llm_thread.LLMChat",
});

registerMessagingComponent(LLMChat);
