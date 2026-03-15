/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, useState } from "@odoo/owl";

/**
 * Component to display LLM tool messages with expandable sections
 */
export class LLMToolMessage extends Component {
  static template = "llm_thread.LLMToolMessage";
  static props = {
    message: { type: Object },
  };

  setup() {
    this.state = useState({
      showArgs: false,
      showResult: false,
    });
  }

  /**
   * Get tool data from message body_json
   */
  get toolData() {
    return this.props.message.body_json || {};
  }

  /**
   * Get tool name
   */
  get toolName() {
    return this.toolData.tool_name || _t("Unknown Tool");
  }

  /**
   * Get tool call ID
   */
  get toolCallId() {
    return this.toolData.tool_call_id || "N/A";
  }

  /**
   * Get tool status
   */
  get status() {
    return this.toolData.status || "unknown";
  }

  /**
   * Check if tool execution was successful
   */
  get isSuccess() {
    return this.status === "completed";
  }

  /**
   * Check if tool execution failed
   */
  get isError() {
    return this.status === "error";
  }

  /**
   * Get tool arguments as formatted JSON
   */
  get argumentsFormatted() {
    const args = this.toolData.arguments || {};
    return JSON.stringify(args, null, 2);
  }

  /**
   * Get tool result as formatted JSON
   */
  get resultFormatted() {
    if (this.isError) {
      return this.toolData.error || _t("Unknown error");
    }
    const result = this.toolData.result;
    if (typeof result === "string") {
      return result;
    }
    return JSON.stringify(result, null, 2);
  }

  /**
   * Get status icon class
   */
  get statusIconClass() {
    if (this.isSuccess) {
      return "fa-check-circle text-success";
    } else if (this.isError) {
      return "fa-exclamation-circle text-danger";
    } else if (this.status === "executing") {
      return "fa-spinner fa-spin text-info";
    }
    return "fa-clock text-muted";
  }

  /**
   * Toggle arguments visibility
   */
  toggleArgs() {
    this.state.showArgs = !this.state.showArgs;
  }

  /**
   * Toggle result visibility
   */
  toggleResult() {
    this.state.showResult = !this.state.showResult;
  }
}
