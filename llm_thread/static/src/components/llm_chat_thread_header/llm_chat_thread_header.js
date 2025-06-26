/** @odoo-module **/
import { registerMessagingComponent } from "@mail/utils/messaging_component";
import { useRefToModel } from "@mail/component_hooks/use_ref_to_model";

const { Component, useState, useRef, onMounted, onWillUnmount, onPatched } =
  owl;

export class LLMChatThreadHeader extends Component {
  /**
   * @override
   */
  setup() {
    super.setup();
    useRefToModel({
      fieldName: "llmChatThreadNameInputRef",
      refName: "threadNameInput",
    });

    // State for model search dropdown
    this.state = useState({
      modelSearchQuery: "",
      shouldShowDropdown: false,
      shouldFocusSearch: false,
    });

    // Refs for dropdown elements
    this.modelDropdownRef = useRef("modelDropdown");
    this.modelSearchInputRef = useRef("modelSearchInput");

    this.onToolSelectChange = this.onToolSelectChange.bind(this);

    // Bind Bootstrap event listeners for better UX
    this._onModelDropdownShown = this._onModelDropdownShown.bind(this);
    this._onModelDropdownHidden = this._onModelDropdownHidden.bind(this);
    this.onSelectModel = this.onSelectModel.bind(this);
    this.onSelectProvider = this.onSelectProvider.bind(this);
    this._preventDropdownClose = this._preventDropdownClose.bind(this);
    this.onModelSearchInput = this.onModelSearchInput.bind(this);

    onMounted(() => {
      if (this.modelDropdownRef.el) {
        this.modelDropdownRef.el.addEventListener(
          "shown.bs.dropdown",
          this._onModelDropdownShown
        );
        this.modelDropdownRef.el.addEventListener(
          "hidden.bs.dropdown",
          this._onModelDropdownHidden
        );
      }
    });

    onWillUnmount(() => {
      if (this.modelDropdownRef.el) {
        this.modelDropdownRef.el.removeEventListener(
          "shown.bs.dropdown",
          this._onModelDropdownShown
        );
        this.modelDropdownRef.el.removeEventListener(
          "hidden.bs.dropdown",
          this._onModelDropdownHidden
        );
      }
    });

    onPatched(() => {
      if (this.state.shouldShowDropdown) {
        const dropdownContainer = this.modelDropdownRef.el;
        if (dropdownContainer) {
          const dropdownTrigger = $(dropdownContainer).find(
            '[data-bs-toggle="dropdown"]'
          );
          if (dropdownTrigger.length) {
            dropdownTrigger.dropdown("show");
          } else {
            console.warn("Model dropdown trigger element not found on patch.");
          }
        } else {
          console.warn("Model dropdown container element not found on patch.");
        }
        // Reset the flag so it doesn't re-show on every patch
        this.state.shouldShowDropdown = false;
      }
      if (this.state.shouldFocusSearch) {
        if (this.modelSearchInputRef.el) {
          this.modelSearchInputRef.el.focus();
          // Reset the flag
          this.state.shouldFocusSearch = false;
        }
      }
    });
  }

  // --------------------------------------------------------------------------
  // Getters
  // --------------------------------------------------------------------------

  get llmChatThreadHeaderView() {
    return this.props.record;
  }

  get threadView() {
    return this.llmChatThreadHeaderView.threadView;
  }

  get thread() {
    return this.threadView.thread;
  }

  get llmChat() {
    return this.thread.llmChat;
  }

  get llmProviders() {
    return this.llmChat.llmProviders;
  }

  get llmModels() {
    // Use the computed property from the view model
    return this.llmChatThreadHeaderView.modelsAvailableToSelect;
  }

  /**
   * Filters the available models based on the search query.
   */
  get filteredModels() {
    const query = this.state.modelSearchQuery.trim().toLowerCase();
    if (!query) {
      // Return all available models if no query
      return this.llmModels;
    }
    return this.llmModels.filter((model) =>
      model.name.toLowerCase().includes(query)
    );
  }

  get isSmall() {
    return this.messaging.device.isSmall;
  }

  // --------------------------------------------------------------------------
  // Event Handlers
  // --------------------------------------------------------------------------

  /**
   * @param {Object} provider
   */
  onSelectProvider(provider) {
    if (provider.id !== this.llmChatThreadHeaderView.selectedProviderId) {
      const defaultModel = this.getDefaultModelForProvider(provider.id);
      // It should trigger saveSelectedModel via the underlying model's compute/onchange
      this.llmChatThreadHeaderView.saveSelectedModel(defaultModel?.id);

      // Clear search when provider changes
      this.state.modelSearchQuery = "";

      this.state.shouldShowDropdown = true;
    }
  }

  getDefaultModelForProvider(providerId) {
    // Note: Use llmChat.llmModels here to check *all* models, not just those already filtered
    const availableModels =
      this.llmChat.llmModels?.filter(
        (model) => model.llmProvider?.id === providerId
      ) || [];
    const defaultModel = availableModels.find((model) => model.default);

    if (defaultModel) {
      return defaultModel;
    } else if (availableModels.length > 0) {
      // Fallback to the first available model if no default is set
      return availableModels[0];
    }
    return null;
  }

  /**
   * @param {Object} model
   */
  onSelectModel(model) {
    this.llmChatThreadHeaderView.saveSelectedModel(model.id);
    // Clear search after selection
    this.state.modelSearchQuery = "";
    // Bootstrap dropdown might close automatically, but clearing state is important
  }

  /**
   * Handle search input changes for models.
   * @param {Event} ev
   */
  onModelSearchInput(ev) {
    this.state.modelSearchQuery = ev.target.value;
  }

  /**
   * Prevents the dropdown from closing when clicking inside the search input or results list.
   * @param {Event} ev
   */
  _preventDropdownClose(ev) {
    ev.stopPropagation();
  }

  /**
   * Focus the search input when the model dropdown is shown.
   */
  _onModelDropdownShown() {
    setTimeout(() => {
      if (this.modelSearchInputRef.el) {
        this.modelSearchInputRef.el.focus();
      }
    }, 0);
  }

  /**
   * Clear the search query when the model dropdown is hidden.
   */
  _onModelDropdownHidden() {
    this.state.modelSearchQuery = "";
  }

  /**
   * Toggle thread list visibility on mobile
   */
  _onToggleThreadList() {
    this.llmChat.llmChatView.update({
      isThreadListVisible: !this.llmChat.llmChatView.isThreadListVisible,
    });
  }

  /**
   * Handle keydown in thread name input
   * @param {KeyboardEvent} ev
   */
  onKeyDownThreadNameInput(ev) {
    switch (ev.key) {
      case "Enter":
        ev.preventDefault();
        this.llmChatThreadHeaderView.saveThreadName();
        break;
      case "Escape":
        ev.preventDefault();
        this.llmChatThreadHeaderView.discardThreadNameEdition();
        break;
    }
  }

  /**
   * Handle input value change
   * @param {Event} ev
   */
  onInputThreadNameInput(ev) {
    this.llmChatThreadHeaderView.update({ pendingName: ev.target.value });
  }

  /**
   * Handle tool selection change
   * @param {Event} ev - The checkbox change event
   * @param {Object} tool - The tool object being selected/deselected
   */
  async onToolSelectChange(ev, tool) {
    const checked = ev.target.checked;

    const currentSelectedIds = this.thread.selectedToolIds || [];
    const newSelectedToolIds = checked
      ? [...currentSelectedIds, tool.id]
      : currentSelectedIds.filter((id) => id !== tool.id);

    // Update the thread settings with the new tool IDs
    await this.thread.updateLLMChatThreadSettings({
      toolIds: newSelectedToolIds,
    });

    // Optimistically update local state (or rely on fetch/reload)
    // It might be better to rely on the reload triggered by onClose of the settings modal
    // or ensure updateLLMChatThreadSettings refreshes the thread record correctly.
    // Let's assume updateLLMChatThreadSettings handles the refresh or is followed by one.
    // For immediate UI feedback, an optimistic update can be done:
    this.thread.update({
      selectedToolIds: newSelectedToolIds,
    });
  }
}

Object.assign(LLMChatThreadHeader, {
  props: { record: Object },
  template: "llm_thread.LLMChatThreadHeader",
});

registerMessagingComponent(LLMChatThreadHeader);
