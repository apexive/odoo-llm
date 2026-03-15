/** @odoo-module **/

import { Component, onMounted, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

/**
 * Dialog for picking a record to link to a thread
 *
 * Two-step process:
 * 1. Select model from dropdown
 * 2. Search and select record from that model
 */
export class RecordPickerDialog extends Component {
  static template = "llm_thread.RecordPickerDialog";
  static components = { Dialog };
  static props = {
    close: Function,
    onConfirm: Function,
  };

  setup() {
    this.state = useState({
      availableModels: [],
      selectedModel: "",
      searchQuery: "",
      searchResults: [],
      selectedRecord: null,
      isLoadingModels: false,
      isSearching: false,
    });

    this.orm = useService("orm");

    // Load available models on mount
    onMounted(() => this.loadAvailableModels());

    // Debounce timer for search
    this.searchTimeout = null;
  }

  // -------------------------------------------------------------------------
  // Model Loading
  // -------------------------------------------------------------------------

  /**
   * Load available models that can be linked
   */
  async loadAvailableModels() {
    try {
      this.state.isLoadingModels = true;

      const result = await this.orm.searchRead(
        "ir.model",
        [
          ["transient", "=", false],
          [
            "model",
            "not in",
            ["mail.message", "mail.followers", "ir.attachment"],
          ],
          ["access_ids", "!=", false],
        ],
        ["model", "name"],
        {
          limit: 100,
          order: "name",
        }
      );

      // Prioritize common business models
      const commonModels = [
        "res.partner",
        "res.users",
        "sale.order",
        "purchase.order",
        "account.move",
        "project.project",
        "project.task",
        "crm.lead",
        "helpdesk.ticket",
        "hr.employee",
        "product.product",
        "product.template",
        "stock.picking",
        "mrp.production",
        "maintenance.request",
      ];

      const prioritizedModels = [];
      const otherModels = [];

      result.forEach((modelData) => {
        if (commonModels.includes(modelData.model)) {
          prioritizedModels.push(modelData);
        } else {
          otherModels.push(modelData);
        }
      });

      // Sort prioritized models by their order in commonModels array
      prioritizedModels.sort((a, b) => {
        const indexA = commonModels.indexOf(a.model);
        const indexB = commonModels.indexOf(b.model);
        return indexA - indexB;
      });

      this.state.availableModels = [...prioritizedModels, ...otherModels];
    } catch (error) {
      console.error("Error loading available models:", error);
      this.state.availableModels = [];
    } finally {
      this.state.isLoadingModels = false;
    }
  }

  // -------------------------------------------------------------------------
  // Model Selection
  // -------------------------------------------------------------------------

  /**
   * Handle model selection change
   * @param {Event} ev - Change event
   */
  onModelChange(ev) {
    this.state.selectedModel = ev.target.value;
    this.state.searchQuery = "";
    this.state.searchResults = [];
    this.state.selectedRecord = null;
  }

  // -------------------------------------------------------------------------
  // Record Search
  // -------------------------------------------------------------------------

  /**
   * Handle search input change (with debouncing)
   * @param {Event} ev - Input event
   */
  onSearchInput(ev) {
    this.state.searchQuery = ev.target.value;

    // Clear previous timeout
    clearTimeout(this.searchTimeout);

    // Debounce search
    this.searchTimeout = setTimeout(() => {
      this.searchRecords();
    }, 300);
  }

  /**
   * Search for records in the selected model
   */
  async searchRecords() {
    const query = this.state.searchQuery.trim();

    // Require minimum 2 characters
    if (!this.state.selectedModel || query.length < 2) {
      this.state.searchResults = [];
      return;
    }

    try {
      this.state.isSearching = true;

      const result = await this.orm.call(
        this.state.selectedModel,
        "name_search",
        [query],
        { limit: 20 }
      );

      this.state.searchResults = result.map(([id, name]) => ({
        id,
        name,
        model: this.state.selectedModel,
      }));
    } catch (error) {
      console.error("Error searching records:", error);
      this.state.searchResults = [];
    } finally {
      this.state.isSearching = false;
    }
  }

  /**
   * Handle search button click
   */
  onSearchClick() {
    this.searchRecords();
  }

  /**
   * Handle Enter key in search input
   * @param {KeyboardEvent} ev - Keyboard event
   */
  onSearchKeydown(ev) {
    if (ev.key === "Enter") {
      this.searchRecords();
    }
  }

  // -------------------------------------------------------------------------
  // Record Selection
  // -------------------------------------------------------------------------

  /**
   * Select a record from search results
   * @param {Object} record - Record object {id, name, model}
   */
  selectRecord(record) {
    this.state.selectedRecord = record;
  }

  /**
   * Check if a record is currently selected
   * @param {Object} record - Record object
   * @returns {Boolean}
   */
  isRecordSelected(record) {
    return this.state.selectedRecord?.id === record.id;
  }

  // -------------------------------------------------------------------------
  // Actions
  // -------------------------------------------------------------------------

  /**
   * Confirm and link the selected record
   */
  confirm() {
    if (this.state.selectedRecord) {
      this.props.onConfirm(
        this.state.selectedRecord.model,
        this.state.selectedRecord.id
      );
      this.props.close();
    }
  }

  /**
   * Check if confirm button should be enabled
   * @returns {Boolean}
   */
  get canConfirm() {
    return Boolean(this.state.selectedRecord);
  }
}
