/** @odoo-module **/

import { registerMessagingComponent } from "@mail/utils/messaging_component";
import { useComponentToModel } from "@mail/component_hooks/use_component_to_model";
const { Component } = owl;

export class LLMChatComposer extends Component {
  /**
   * @override
   */
  setup() {
    super.setup();
    useComponentToModel({ fieldName: "component" });
  }

  /**
   * @returns {ComposerView}
   */
  get composerView() {
    return this.props.record;
  }

  /**
   * @returns {Boolean}
   */
  get isSendDisabled() {
    // Read the computed disabled state from the model.
    return this.composerView.composer.isSendDisabled;
  }

  /**
   * @returns {Boolean}
   */
  get isContinueDisabled() {
    return this.composerView.composer.isContinueDisabled;
  }

  get isStreaming() {
    return this.composerView.composer.isStreaming;
  }

  // --------------------------------------------------------------------------
  // Private
  // --------------------------------------------------------------------------

  /**
   * Intercept send button click
   * @private
   */
  _onClickSend() {
    if (this.isSendDisabled) {
      return;
    }

    this.composerView.composer.postUserMessageForLLM();
  }

  /**
   * Intercept continue button click
   * @private
   */
  _onClickContinue() {
    if (this.isContinueDisabled) {
      return;
    }

    this.composerView.composer.repostExistingUserMessagesForLLM();
  }

  /**
   * Handles click on the stop button.
   *
   * @private
   */
  _onClickStop() {
    this.composerView.composer.stopLLMThreadLoop();
  }
}

Object.assign(LLMChatComposer, {
  props: { record: Object },
  template: "llm_thread.LLMChatComposer",
});

registerMessagingComponent(LLMChatComposer);
