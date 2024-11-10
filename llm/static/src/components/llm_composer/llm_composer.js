/** @odoo-module **/

import {
  Component,
  useState,
  useRef,
  onMounted,
  onWillUnmount,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

const TEXTAREA_MIN_HEIGHT = 60;
const TEXTAREA_MAX_HEIGHT = 200;

/**
 * Composer component for LLM chat interface
 */
export class LLMComposer extends Component {
  setup() {
    // Refs
    this.textareaRef = useRef("textarea");
    this.mirroredTextareaRef = useRef("mirroredTextarea");

    // Services
    this.uiService = useService("ui");

    // Local state
    this.state = useState({
      content: "",
      isDisabled: false,
    });

    // Command history
    this.commandHistory = [];
    this.historyIndex = -1;

    // Bind methods
    this.onInputThrottled = _.throttle(this._onInput.bind(this), 100);
  }

  /**
   * @returns {string} The current content
   */
  get content() {
    return this.state.content;
  }

  /**
   * @returns {string} Placeholder text
   */
  get placeholder() {
    return this.props.placeholder || this.env._t("Type a message...");
  }

  /**
   * @returns {boolean} Whether composer is disabled
   */
  get isDisabled() {
    return this.props.isDisabled || this.state.isDisabled;
  }

  /**
   * @returns {boolean} Whether submit is allowed
   */
  get canSubmit() {
    return !this.isDisabled && this.content.trim().length > 0;
  }

  /**
   * Handle input changes
   * @private
   */
  _onInput() {
    if (!this.textareaRef.el) return;

    const content = this.textareaRef.el.value;
    this.state.content = content;

    // Notify parent of content change
    this.props.onContentChange?.(content);
  }

  /**
   * Handle key events
   * @param {KeyboardEvent} ev
   * @private
   */
  _onKeydown(ev) {
    // Handle submit on Enter (without shift)
    if (ev.key === "Enter" && !ev.shiftKey && !ev.ctrlKey && !ev.metaKey) {
      ev.preventDefault();
      this._onSubmit();
      return;
    }

    // Command history navigation
    if (ev.key === "ArrowUp" && !ev.shiftKey && this.content.trim() === "") {
      ev.preventDefault();
      this._navigateHistory("up");
      return;
    }
    if (ev.key === "ArrowDown" && !ev.shiftKey && this.content.trim() === "") {
      ev.preventDefault();
      this._navigateHistory("down");
      return;
    }
  }

  /**
   * Navigate command history
   * @param {string} direction 'up' or 'down'
   * @private
   */
  _navigateHistory(direction) {
    if (!this.commandHistory.length) return;

    if (direction === "up") {
      this.historyIndex = Math.min(
        this.historyIndex + 1,
        this.commandHistory.length - 1
      );
    } else {
      this.historyIndex = Math.max(this.historyIndex - 1, -1);
    }

    const content =
      this.historyIndex >= 0 ? this.commandHistory[this.historyIndex] : "";
    this.state.content = content;
    if (this.textareaRef.el) {
      this.textareaRef.el.value = content;
    }
  }

  /**
   * Handle message submission
   * @private
   */
  _onSubmit() {
    if (!this.canSubmit) return;

    const content = this.content.trim();
    if (!content) return;

    // Add to command history if unique
    if (!this.commandHistory.includes(content)) {
      this.commandHistory.unshift(content);
      if (this.commandHistory.length > 50) {
        this.commandHistory.pop();
      }
    }
    this.historyIndex = -1;

    // Notify parent
    this.props.onSubmit(content);

    // Clear content
    this._clearContent();
  }

  /**
   * Clear textarea content
   * @private
   */
  _clearContent() {
    this.state.content = "";
    if (this.textareaRef.el) {
      this.textareaRef.el.value = "";
    }
  }

  /**
   * Handle paste event
   * @param {ClipboardEvent} ev
   * @private
   */
  _onPaste(ev) {
    // Handle paste events if needed
  }
}

LLMComposer.components = {};
LLMComposer.template = "llm.Composer";

LLMComposer.props = {
  placeholder: { type: String, optional: true },
  isDisabled: { type: Boolean, optional: true },
  onSubmit: { type: Function, required: true },
  onContentChange: { type: Function, optional: true },
  className: { type: String, optional: true },
};

registry.category("components").add("LLMComposer", LLMComposer);
