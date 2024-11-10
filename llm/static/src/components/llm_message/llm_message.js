/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useRef } from "@odoo/owl";
import { markdownToHtml } from "@web/core/utils/markdown"; // Assuming Odoo provides markdown utils

export class LLMMessage extends Component {
  setup() {
    super.setup();
    this.contentRef = useRef("content");
    this.prettyBodyRef = useRef("prettyBody");
  }

  /**
   * @returns {boolean}
   */
  get isUserMessage() {
    return this.props.message.role === "user";
  }

  /**
   * @returns {string}
   */
  get authorName() {
    if (this.isUserMessage) {
      return this.env.session.name;
    }
    return this.props.message.author || "Assistant";
  }

  /**
   * @returns {string}
   */
  get formattedDate() {
    if (!this.props.message.timestamp) {
      return "";
    }
    return new Date(this.props.message.timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  /**
   * Handles markdown content updates
   */
  async onContentMounted() {
    if (this.contentRef.el && this.props.message.content) {
      const html = await markdownToHtml(this.props.message.content);
      if (this.prettyBodyRef.el) {
        this.prettyBodyRef.el.innerHTML = html;
      }
    }
  }
}

LLMMessage.template = "llm.Message";
LLMMessage.props = {
  message: {
    type: Object,
    shape: {
      id: String,
      content: String,
      role: String,
      author: { type: String, optional: true },
      timestamp: { type: String, optional: true },
    },
  },
  className: { type: String, optional: true },
};
