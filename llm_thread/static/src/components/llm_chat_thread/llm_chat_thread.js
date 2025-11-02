/** @odoo-module **/

import { registerMessagingComponent } from "@mail/utils/messaging_component";

const { Component } = owl;

export class LLMChatThread extends Component {
  get threadView() {
    return this.props.threadView;
  }

  /**
   * @returns {Thread}
   */
  get thread() {
    return this.props.record;
  }

  /**
   * @returns {Message[]}
   */
  get messages() {
    // Use ThreadCache's orderedMessages
    return this.thread.cache?.orderedMessages || [];
  }
}

Object.assign(LLMChatThread, {
  props: {
    record: Object,
    threadView: Object,
  },
  template: "llm_thread.LLMChatThread",
});

registerMessagingComponent(LLMChatThread);
