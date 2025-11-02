/** @odoo-module **/

import { attr, many, one } from "@mail/model/model_field";
import { clear } from "@mail/model/model_field_command";
import { registerModel } from "@mail/model/model_core";

registerModel({
  name: "LLMChatThreadHeaderView",
  lifecycleHooks: {
    _created() {
      // Set initial values without triggering backend update
      this._initializeState();
    },
  },
  fields: {
    threadView: one("ThreadView", {
      inverse: "llmChatThreadHeaderView",
    }),
    isEditingName: attr({
      default: false,
    }),
    pendingName: attr({
      default: "",
    }),
    llmChatThreadNameInputRef: attr(),
    selectedProviderId: attr(),
    selectedModelId: attr(),
    _isInitializing: attr({
      default: false,
    }),
    selectedProvider: one("LLMProvider", {
      compute() {
        if (!this.selectedProviderId) {
          return clear();
        }
        const providers = this.threadView?.thread?.llmChat?.llmProviders;
        if (!providers || !Array.isArray(providers)) {
          return clear();
        }
        return (
          providers.find((p) => p && p.id === this.selectedProviderId) ||
          clear()
        );
      },
    }),
    selectedModel: one("LLMModel", {
      compute() {
        if (!this.selectedModelId) {
          return clear();
        }
        const models = this.threadView?.thread?.llmChat?.llmModels;
        if (!models || !Array.isArray(models)) {
          return clear();
        }
        const matchedModel = models.find(
          (m) => m && m.id === this.selectedModelId
        );
        return matchedModel || clear();
      },
    }),
    modelsAvailableToSelect: many("LLMModel", {
      compute() {
        if (!this.selectedProviderId) {
          return [];
        }
        return (
          this.threadView?.thread?.llmChat?.llmModels?.filter(
            (model) => model?.llmProvider?.id === this.selectedProviderId
          ) || []
        );
      },
    }),
  },
  recordMethods: {
    /**
     * Initialize or reset state based on current thread
     * @private
     */
    _initializeState() {
      const currentThread = this.threadView?.thread;
      if (!currentThread) {
        this.update({
          selectedProviderId: clear(),
          selectedModelId: clear(),
        });
        return;
      }

      this.update({
        selectedProviderId: currentThread.llmModel?.llmProvider?.id,
        selectedModelId: currentThread.llmModel?.id,
      });
    },

    /**
     * Handle thread changes
     * @private
     */
    _onThreadViewChange() {
      this._initializeState();
    },

    /**
     * Handle model changes
     * @param {String} selectedModelId - ID of the selected model
     * @private
     */
    async saveSelectedModel(selectedModelId) {
      // Skip backend update during initialization
      if (!selectedModelId || selectedModelId === this.selectedModelId) {
        return;
      }

      this.update({
        selectedModelId,
      });
      const provider = this.selectedModel.llmProvider;
      this.update({
        selectedProviderId: provider.id,
      });

      await this.threadView.thread.updateLLMChatThreadSettings({
        llmModelId: this.selectedModel.id,
        llmProviderId: provider.id,
      });
    },

    /**
     * Opens the thread form view for editing
     */
    async openThreadSettings() {
      await this.env.services.action.doAction(
        {
          type: "ir.actions.act_window",
          res_model: "llm.thread",
          res_id: this.threadView.thread.id,
          views: [[false, "form"]],
          target: "new",
          flags: {
            mode: "edit",
          },
        },
        {
          onClose: () => {
            // Reload thread data when form is closed
            this.threadView.thread.llmChat.loadThreads();
          },
        }
      );
    },

    /**
     * Start editing thread name
     */
    onClickTopbarThreadName() {
      if (this.isEditingName || this.messaging.device.isSmall) {
        return;
      }
      this.update({
        isEditingName: true,
        pendingName: this.threadView.thread.name,
      });
    },

    /**
     * Save thread name changes to server
     */
    async saveThreadName() {
      const thread = this.threadView.thread;
      if (!this.pendingName.trim()) {
        this.discardThreadNameEdition();
        return;
      }

      const newName = this.pendingName.trim();
      if (newName === thread.name) {
        this.discardThreadNameEdition();
        return;
      }

      try {
        await thread.updateLLMChatThreadSettings({ name: newName });
        this.update({
          isEditingName: false,
          pendingName: "",
        });
      } catch (error) {
        console.error("Error updating thread name:", error);
        this.messaging.notify({
          message: this.env._t("Failed to update thread name"),
          type: "danger",
        });
        this.discardThreadNameEdition();
      }
    },

    /**
     * Discard thread name changes
     */
    discardThreadNameEdition() {
      this.update({
        isEditingName: false,
        pendingName: "",
      });
    },
  },
  onChanges: [
    {
      dependencies: ["threadView.thread.llmChat.activeThread.id"],
      methodName: "_onThreadViewChange",
    },
  ],
});
