/** @odoo-module **/
import { ComposerTextInput } from "@mail/components/composer_text_input/composer_text_input";
import { registerMessagingComponent } from "@mail/utils/messaging_component";

export class LLMChatComposerTextInput extends ComposerTextInput {
  /**
   * @override
   */
  setup() {
    super.setup();
    this._composerView();
  }
  /**
   * Intercept input event before passing to composer view
   * @private
   * @param {InputEvent} ev
   */
  _onInput(ev) {
    // Call original handler
    this._composerView();
    this.composerView.onInputTextarea(ev);
  }

  _composerView() {
    return this.props.record;
  }

  /**
   * Intercept keydown event
   * @private
   * @param {KeyboardEvent} ev
   */
  _onKeydown(ev) {
    this.composerView.onKeydownTextareaForLLM(ev);
  }
}

Object.assign(LLMChatComposerTextInput, {
  props: { record: Object },
  template: "llm_thread.LLMChatComposerTextInput",
});

registerMessagingComponent(LLMChatComposerTextInput);
