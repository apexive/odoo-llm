/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registerMessagingComponent } from "@mail/utils/messaging_component";

export class LLMStreamingIndicator extends Component {
  setup() {
    this.state = useState({ dots: "" });
    let count = 0;
    onMounted(() => {
      this.interval = setInterval(() => {
        count = (count + 1) % 4;
        this.state.dots = ".".repeat(count);
      }, 500);
    });
    onWillUnmount(() => {
      clearInterval(this.interval);
    });
  }
}
Object.assign(LLMStreamingIndicator, {
  template: "llm_thread.LLMStreamingIndicator",
});

registerMessagingComponent(LLMStreamingIndicator);
