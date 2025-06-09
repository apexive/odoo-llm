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
  get isRegenerateDisabled() {
    return this.composerView.composer.isRegenerateDisabled;
  }

  get isStreaming() {
    return this.composerView.composer.isStreaming;
  }

  // --------------------------------------------------------------------------
  // Private
  // --------------------------------------------------------------------------

  /**
   * Intercept send / regenerate button click
   * @private
   */
  _onMessageSendOrRegenerate() {
    if (!this.isSendDisabled) {
      this.composerView.composer.postUserMessageForLLM();
      return;
    }

    if (!this.isRegenerateDisabled) {
      this.composerView.composer.repostExistingUserMessagesForLLM();
      return;
    }
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
