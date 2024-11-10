/** @odoo-module **/

import { Component, useRef, onMounted, onWillUnmount } from "@odoo/owl";
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

    // Command history
    this.commandHistory = [];
    this.historyIndex = -1;

    // Bind methods
    this.onInputThrottled = _.throttle(this._onInput.bind(this), 100);
    this.updateTextareaHeight = _.throttle(this._updateTextareaHeight.bind(this), 16);

    // Setup lifecycle hooks
    onMounted(() => this._mounted());
    onWillUnmount(() => this._cleanup());

    // Setup auto-resize observer
    this._setupResizeObserver();
  }

  /**
   * @returns {Object} The composer record from props
   */
  get composerView() {
    return this.props.record;
  }

  /**
   * @returns {string} The current content
   */
  get content() {
    return this.composerView.content || '';
  }

  /**
   * @returns {string} Placeholder text
   */
  get placeholder() {
    return this.composerView.placeholder || this.env._t("Type a message...");
  }

  /**
   * @returns {boolean} Whether composer is disabled
   */
  get isDisabled() {
    return this.composerView.isDisabled;
  }

  /**
   * @returns {boolean} Whether submit is allowed
   */
  get canSubmit() {
    return !this.isDisabled && this.content.trim().length > 0;
  }

  /**
   * Component mounted hook
   * @private
   */
  _mounted() {
    if (this.textareaRef.el) {
      this.textareaRef.el.focus();
      this._updateTextareaHeight();
    }
  }

  /**
   * Clean up resources
   * @private
   */
  _cleanup() {
    if (this.onInputThrottled?.cancel) {
      this.onInputThrottled.cancel();
    }
    if (this.updateTextareaHeight?.cancel) {
      this.updateTextareaHeight.cancel();
    }
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
  }

  /**
   * Setup resize observer
   * @private
   */
  _setupResizeObserver() {
    this.resizeObserver = new ResizeObserver(() => {
      this._updateTextareaHeight();
    });
  }

  /**
   * Update textarea height based on content
   * @private
   */
  _updateTextareaHeight() {
    const textarea = this.textareaRef.el;
    const mirroredTextarea = this.mirroredTextareaRef.el;
    if (!textarea || !mirroredTextarea) return;

    // Copy content to mirrored textarea
    mirroredTextarea.value = textarea.value;
    textarea.style.height = 'auto';

    // Calculate and set new height
    const newHeight = Math.min(
        Math.max(mirroredTextarea.scrollHeight, TEXTAREA_MIN_HEIGHT),
        TEXTAREA_MAX_HEIGHT
    );
    textarea.style.height = `${newHeight}px`;

    // Update scroll status if at max height
    textarea.classList.toggle('o-is-scrollable', mirroredTextarea.scrollHeight > TEXTAREA_MAX_HEIGHT);
  }

  /**
   * Handle input changes
   * @private
   */
  _onInput() {
    if (!this.textareaRef.el) return;

    const content = this.textareaRef.el.value;
    this.updateTextareaHeight();

    // Update model
    this.composerView.update({ content });
  }

  /**
   * Handle key events
   * @param {KeyboardEvent} ev
   * @private
   */
  _onKeydown(ev) {
    // Handle submit on Enter (without shift)
    if (ev.key === 'Enter' && !ev.shiftKey && !ev.ctrlKey && !ev.metaKey) {
      ev.preventDefault();
      this._onSubmit();
      return;
    }

    // Command history navigation
    if (ev.key === 'ArrowUp' && !ev.shiftKey && this.content.trim() === '') {
      ev.preventDefault();
      this._navigateHistory('up');
      return;
    }
    if (ev.key === 'ArrowDown' && !ev.shiftKey && this.content.trim() === '') {
      ev.preventDefault();
      this._navigateHistory('down');
      return;
    }

    // Handle common keyboard shortcuts
    if (ev.key === 'l' && (ev.ctrlKey || ev.metaKey)) {
      ev.preventDefault();
      this._clearContent();
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

    if (direction === 'up') {
      this.historyIndex = Math.min(this.historyIndex + 1, this.commandHistory.length - 1);
    } else {
      this.historyIndex = Math.max(this.historyIndex - 1, -1);
    }

    const content = this.historyIndex >= 0 ? this.commandHistory[this.historyIndex] : '';
    this._setContent(content);
  }

  /**
   * Set textarea content
   * @param {string} content
   * @private
   */
  _setContent(content) {
    if (!this.textareaRef.el) return;

    this.textareaRef.el.value = content;
    this.composerView.update({ content });
    this._updateTextareaHeight();

    // Move cursor to end
    this.textareaRef.el.setSelectionRange(content.length, content.length);
  }

  /**
   * Clear textarea content
   * @private
   */
  _clearContent() {
    this._setContent('');
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

    // Submit message
    this.props.onSubmit(content);

    // Clear composer
    this._clearContent();
  }

  /**
   * Handle paste events
   * @param {ClipboardEvent} ev
   * @private
   */
  _onPaste(ev) {
    // Handle file paste
    const files = Array.from(ev.clipboardData?.files || []);
    if (files.length) {
      ev.preventDefault();
      this.props.onFilesPasted?.(files);
      return;
    }

    // Handle text paste
    const text = ev.clipboardData?.getData('text/plain');
    if (text) {
      // Let default paste behavior handle it
      this.updateTextareaHeight();
    }
  }
}

LLMComposer.template = "llm.Composer";

LLMComposer.props = {
  record: {
    type: Object,
    required: true,
  },
  onSubmit: {
    type: Function,
    required: true,
  },
  onFilesPasted: {
    type: Function,
    optional: true,
  },
  className: {
    type: String,
    optional: true,
  }
};

// Register the component
registry.category("components").add("LLMComposer", LLMComposer);
