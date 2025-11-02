/** @odoo-module **/

import { Component, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

/**
 * Thread Header Component
 * Displays thread name and provides dropdowns for provider/model/tool selection
 */
export class LLMThreadHeader extends Component {
  static template = "llm_thread.LLMThreadHeader";
  static components = { Dropdown, DropdownItem };

  setup() {
    this.llmStore = useState(useService("llm.store"));
    this.mailStore = useState(useService("mail.store"));
    this.orm = useService("orm");
    this.notification = useService("notification");

    // Local state
    this.state = useState({
      isEditingName: false,
      pendingName: "",
      modelSearchQuery: "",
      isLoadingUpdate: false,
    });

    // Refs
    this.nameInputRef = useRef("nameInput");
  }

  /**
   * Get the active thread
   */
  get activeThread() {
    return this.mailStore.discuss?.thread;
  }

  /**
   * Check if we have an active LLM thread
   */
  get hasActiveThread() {
    return this.activeThread?.model === "llm.thread";
  }

  /**
   * Get current provider
   */
  get currentProvider() {
    if (!this.hasActiveThread) return null;

    // Get provider_id from the thread data (now stored in mailStore)
    const providerId =
      this.activeThread.provider_id?.id || this.activeThread.provider_id;
    if (!providerId) return null;

    // Return provider from our Map or directly from thread if available
    return (
      this.llmStore.llmProviders?.get(providerId) ||
      this.activeThread.provider_id
    );
  }

  /**
   * Get current model
   */
  get currentModel() {
    if (!this.hasActiveThread) return null;

    // Get model_id from the thread data (now stored in mailStore)
    const modelId =
      this.activeThread.model_id?.id || this.activeThread.model_id;
    if (!modelId) return null;

    // Return model from our Map or directly from thread if available
    return this.llmStore.llmModels?.get(modelId) || this.activeThread.model_id;
  }

  /**
   * Get available providers
   */
  get availableProviders() {
    return Array.from(this.llmStore.llmProviders.values());
  }

  /**
   * Get available models for current provider
   */
  get availableModels() {
    if (!this.currentProvider) return [];

    // Filter models by provider
    const models = Array.from(this.llmStore.llmModels.values()).filter(
      (model) => {
        const modelProviderId = Array.isArray(model.provider_id)
          ? model.provider_id[0]
          : model.provider_id;
        return modelProviderId === this.currentProvider.id;
      }
    );

    // Apply search filter if any
    if (this.state.modelSearchQuery) {
      const query = this.state.modelSearchQuery.toLowerCase();
      return models.filter((model) => model.name.toLowerCase().includes(query));
    }

    return models;
  }

  /**
   * Get current tools
   */
  get currentTools() {
    if (!this.hasActiveThread) return [];

    // Get tool_ids from the thread data (now stored in mailStore)
    const toolIds = this.activeThread.tool_ids || [];
    if (!toolIds.length) return [];

    // Handle different formats: array of objects or array of IDs
    return toolIds
      .map((tool) => {
        if (typeof tool === "object" && tool.id) {
          return this.llmStore.llmTools?.get(tool.id) || tool;
        }
        return this.llmStore.llmTools?.get(tool);
      })
      .filter(Boolean);
  }

  /**
   * Get available tools
   */
  get availableTools() {
    return this.llmStore.llmTools
      ? Array.from(this.llmStore.llmTools.values())
      : [];
  }

  // Thread Name Management

  /**
   * Start editing thread name
   */
  startEditingName() {
    this.state.isEditingName = true;
    this.state.pendingName = this.activeThread.name || "";

    // Focus input after render
    setTimeout(() => {
      if (this.nameInputRef.el) {
        this.nameInputRef.el.focus();
        this.nameInputRef.el.select();
      }
    }, 0);
  }

  /**
   * Save thread name
   */
  async saveThreadName() {
    if (!this.state.pendingName.trim()) {
      this.notification.add("Thread name cannot be empty", {
        type: "warning",
      });
      return;
    }

    try {
      this.state.isLoadingUpdate = true;

      // Update thread name via ORM
      await this.orm.write("llm.thread", [this.activeThread.id], {
        name: this.state.pendingName.trim(),
      });

      // Reload thread data using proper fetchData pattern
      await this.activeThread.fetchData(["name"]);

      this.state.isEditingName = false;
      this.state.pendingName = "";
    } catch (error) {
      this.notification.add("Failed to update thread name", {
        type: "danger",
      });
      console.error("Error updating thread name:", error);
    } finally {
      this.state.isLoadingUpdate = false;
    }
  }

  /**
   * Cancel editing thread name
   */
  cancelEditingName() {
    this.state.isEditingName = false;
    this.state.pendingName = "";
  }

  /**
   * Handle keydown in name input
   */
  onNameInputKeydown(ev) {
    if (ev.key === "Enter") {
      ev.preventDefault();
      this.saveThreadName();
    } else if (ev.key === "Escape") {
      ev.preventDefault();
      this.cancelEditingName();
    }
  }

  // Provider Management

  /**
   * Select a provider
   */
  async selectProvider(provider) {
    if (provider.id === this.currentProvider?.id) return;

    try {
      this.state.isLoadingUpdate = true;

      // Get default model for this provider
      const models = Array.from(this.llmStore.llmModels.values()).filter(
        (m) => m.provider_id[0] === provider.id
      );
      const defaultModel = models.find((m) => m.is_default) || models[0];

      const updateData = {
        provider_id: provider.id,
      };

      if (defaultModel) {
        updateData.model_id = defaultModel.id;
      }

      // Update via ORM
      await this.orm.write("llm.thread", [this.activeThread.id], updateData);

      // Reload thread data using proper fetchData pattern
      await this.activeThread.fetchData(["provider_id", "model_id"]);
    } catch (error) {
      this.notification.add("Failed to update provider", {
        type: "danger",
      });
      console.error("Error updating provider:", error);
    } finally {
      this.state.isLoadingUpdate = false;
    }
  }

  // Model Management

  /**
   * Select a model
   */
  async selectModel(model) {
    if (model.id === this.currentModel?.id) return;

    try {
      this.state.isLoadingUpdate = true;

      // Update via ORM
      await this.orm.write("llm.thread", [this.activeThread.id], {
        model_id: model.id,
      });

      // Reload thread data using proper fetchData pattern
      await this.activeThread.fetchData(["model_id"]);

      // Clear search
      this.state.modelSearchQuery = "";
    } catch (error) {
      this.notification.add("Failed to update model", {
        type: "danger",
      });
      console.error("Error updating model:", error);
    } finally {
      this.state.isLoadingUpdate = false;
    }
  }

  /**
   * Handle model search input
   */
  onModelSearchInput(ev) {
    this.state.modelSearchQuery = ev.target.value;
  }

  /**
   * Clear model search
   */
  clearModelSearch() {
    this.state.modelSearchQuery = "";
  }

  // Tool Management

  /**
   * Toggle tool selection
   */
  async toggleTool(tool) {
    try {
      this.state.isLoadingUpdate = true;

      // Get current tool IDs from the active thread
      const currentToolIds = (this.activeThread.tool_ids || []).map((tool) =>
        typeof tool === "object" ? tool.id : tool
      );

      const newToolIds = currentToolIds.includes(tool.id)
        ? currentToolIds.filter((id) => id !== tool.id)
        : [...currentToolIds, tool.id];

      // Update via ORM
      await this.orm.write("llm.thread", [this.activeThread.id], {
        tool_ids: [[6, 0, newToolIds]],
      });

      // Immediately update local state to ensure UI reflects change
      this.activeThread.tool_ids = newToolIds;

      // Reload thread data using proper fetchData pattern
      await this.activeThread.fetchData(["tool_ids"]);
    } catch (error) {
      this.notification.add("Failed to update tools", {
        type: "danger",
      });
      console.error("Error updating tools:", error);
    } finally {
      this.state.isLoadingUpdate = false;
    }
  }

  /**
   * Check if a tool is selected
   */
  isToolSelected(tool) {
    if (!this.hasActiveThread) return false;

    // Check if tool is in the current thread's tool_ids
    const toolIds = (this.activeThread.tool_ids || []).map((t) =>
      typeof t === "object" ? t.id : t
    );
    return toolIds.includes(tool.id);
  }
}

LLMThreadHeader.props = {
  thread: { type: Object, optional: true },
};
