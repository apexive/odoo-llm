/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

/**
 * Simplified message component for displaying LLM chat messages
 */
export class LLMMessage extends Component {
  setup() {
    this.notification = useService("notification");
  }

  /**
   * @returns {Object} The message record from props
   */
  get message() {
    return this.props.record;
  }

  /**
   * @returns {boolean} Whether message is from user
   */
  get isUserMessage() {
    return this.message.role === "user";
  }

  /**
   * @returns {string} Author name
   */
  get authorName() {
    return (
      this.message.author ||
      (this.isUserMessage ? this.env.session.name : "Assistant")
    );
  }

  /**
   * @returns {string} Formatted time
   */
  get formattedDate() {
    return this.message.formattedTime;
  }

  /**
   * @returns {string} Status-based CSS class
   */
  get statusClass() {
    switch (this.message.status) {
      case "sending":
        return "text-muted";
      case "error":
        return "text-danger";
      default:
        return "";
    }
  }

  /**
   * @returns {boolean} Whether to show retry button
   */
  get showRetry() {
    return this.message.status === "error" && !this.isUserMessage;
  }

  /**
   * Handle retry button click
   */
  onRetryClick() {
    if (this.props.onRetry) {
      this.props.onRetry(this.message);
    }
  }

  /**
   * Handle copy button click
   */
  async onCopyClick() {
    try {
      await navigator.clipboard.writeText(this.message.content);
      this.notification.add(this.env._t("Copied to clipboard"), {
        type: "success",
        sticky: false,
      });
    } catch (error) {
      this.notification.add(this.env._t("Failed to copy message"), {
        type: "danger",
        sticky: false,
      });
    }
  }
}

LLMMessage.template = "llm.Message";

LLMMessage.props = {
  record: { type: Object, required: true },
  className: { type: String, optional: true },
  onRetry: { type: Function, optional: true },
};

registry.category("components").add("LLMMessage", LLMMessage);
