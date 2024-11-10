/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useRefToModel } from "@mail/component_hooks/use_ref_to_model";
import { useUpdate } from "@mail/component_hooks/use_update";

export class LLMComposer extends Component {
  setup() {
    super.setup();
    this.textareaRef = useRefToModel({ refName: "textarea" });
    this.mirroredTextareaRef = useRefToModel({ refName: "mirroredTextarea" });

    useUpdate({ func: () => this._update() });

    this._onInputThrottled = _.throttle(this._onInput.bind(this), 100);
  }

  /**
   * @returns {ComposerView}
   */
  get composerView() {
    return this.props.record;
  }

  /**
   * Updates the content and height of textarea
   * @private
   */
  _update() {
    if (!this.textareaRef.el) {
      return;
    }

    // Handle focus if needed
    if (this.composerView.shouldFocus) {
      this.composerView.update({ shouldFocus: false });
      this.textareaRef.el.focus();
    }

    // Update content if needed
    if (this.composerView.hasToRestoreContent) {
      this.textareaRef.el.value = this.composerView.textInputContent;
      this.composerView.update({ hasToRestoreContent: false });
    }

    this._updateTextareaHeight();
  }

  /**
   * Updates textarea height to match content
   * @private
   */
  _updateTextareaHeight() {
    const textarea = this.textareaRef.el;
    const mirroredTextarea = this.mirroredTextareaRef.el;

    if (!textarea || !mirroredTextarea) {
      return;
    }

    // Copy content to mirrored textarea to calculate height
    mirroredTextarea.value = textarea.value;

    // Reset textarea height to allow shrinking
    textarea.style.height = "auto";

    // Set new height based on scrollHeight
    const newHeight = Math.min(
      Math.max(mirroredTextarea.scrollHeight, 60), // min 60px
      200 // max 200px
    );
    textarea.style.height = `${newHeight}px`;
  }

  /**
   * @private
   * @param {InputEvent} ev
   */
  _onInput(ev) {
    if (!this.textareaRef.el) {
      return;
    }

    this._updateTextareaHeight();

    this.composerView.update({
      textInputContent: this.textareaRef.el.value,
    });
  }

  /**
   * @private
   * @param {KeyboardEvent} ev
   */
  _onKeydown(ev) {
    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      this._onSend();
    }
  }

  /**
   * Send the message
   * @private
   */
  _onSend() {
    const content = this.textareaRef.el.value.trim();
    if (!content) {
      return;
    }

    this.composerView.onSend(content);
    this.textareaRef.el.value = "";
    this._updateTextareaHeight();
  }
}

Object.assign(LLMComposer, {
  props: { record: Object },
  template: "llm.Composer",
});
