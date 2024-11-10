/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useRef } from "@odoo/owl";
import { useUpdate } from "@web/core/utils/update";

export class LLMComposer extends Component {
  setup() {
    super.setup();
    this.textareaRef = useRef("textarea");
    this.mirroredTextareaRef = useRef("mirroredTextarea");

    useUpdate({ func: () => this._update() });
    this._onInputThrottled = _.throttle(this._onInput.bind(this), 100);
  }

  get composerView() {
    return this.props.record;
  }

  _update() {
    if (!this.textareaRef.el) return;

    if (this.composerView.shouldFocus) {
      this.composerView.update({ shouldFocus: false });
      this.textareaRef.el.focus();
    }

    if (this.composerView.hasToRestoreContent) {
      this.textareaRef.el.value = this.composerView.textInputContent;
      this.composerView.update({ hasToRestoreContent: false });
    }

    this._updateTextareaHeight();
  }

  _updateTextareaHeight() {
    const textarea = this.textareaRef.el;
    const mirroredTextarea = this.mirroredTextareaRef.el;
    if (!textarea || !mirroredTextarea) return;

    mirroredTextarea.value = textarea.value;
    textarea.style.height = "auto";

    const newHeight = Math.min(
        Math.max(mirroredTextarea.scrollHeight, 60),
        200
    );
    textarea.style.height = `${newHeight}px`;
  }

  _onInput() {
    if (!this.textareaRef.el) return;
    this._updateTextareaHeight();
    this.composerView.update({
      textInputContent: this.textareaRef.el.value,
    });
  }

  _onKeydown(ev) {
    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      this._onSend();
    }
  }

  _onSend() {
    const content = this.textareaRef.el.value.trim();
    if (!content) return;

    this.props.onSubmit(content);
    this.textareaRef.el.value = "";
    this._updateTextareaHeight();
  }
}

LLMComposer.props = {
  record: Object,
  onSubmit: Function,
  className: { type: String, optional: true },
};

LLMComposer.template = "llm.Composer";
