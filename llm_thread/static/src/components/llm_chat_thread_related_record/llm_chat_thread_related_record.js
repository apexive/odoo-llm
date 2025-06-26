/** @odoo-module **/

import { registerMessagingComponent } from "@mail/utils/messaging_component";
import { useModels } from "@mail/component_hooks/use_models";

const { Component, useState, onMounted } = owl;

export class LLMChatThreadRelatedRecord extends Component {
  setup() {
    useModels();
    super.setup();

    this.state = useState({
      relatedRecordDisplayName: "",
      isLoading: false,
    });

    onMounted(() => {
      this._loadRelatedRecordDisplayName();
    });

    // Bind methods
    this.onClickRelatedRecord = this.onClickRelatedRecord.bind(this);
    this.onClickChooseRecord = this.onClickChooseRecord.bind(this);
    this.onClickUnlinkRecord = this.onClickUnlinkRecord.bind(this);
  }

  // --------------------------------------------------------------------------
  // Getters
  // --------------------------------------------------------------------------

  /**
   * @returns {Thread}
   */
  get thread() {
    return this.props.thread;
  }

  /**
   * @returns {Boolean}
   */
  get isSmall() {
    return this.messaging.device.isSmall;
  }

  /**
   * @returns {String}
   */
  get relatedRecordDisplayName() {
    return this.state.relatedRecordDisplayName;
  }

  /**
   * @returns {Boolean}
   */
  get hasRelatedRecord() {
    return Boolean(this.thread.relatedThread);
  }

  // --------------------------------------------------------------------------
  // Related Record Methods
  // --------------------------------------------------------------------------

  /**
   * Load the display name of the related record
   * @private
   */
  async _loadRelatedRecordDisplayName() {
    if (!this.thread.relatedThread) {
      this.state.relatedRecordDisplayName = "";
      return;
    }

    try {
      this.state.isLoading = true;
      const result = await this.messaging.rpc({
        model: this.thread.relatedThreadModel,
        method: "name_get",
        args: [[this.thread.relatedThreadId]],
      });

      if (result && result.length > 0) {
        this.state.relatedRecordDisplayName = result[0][1];
      }
    } catch (error) {
      console.error("Error loading related record display name:", error);
      this.state.relatedRecordDisplayName = "";
    } finally {
      this.state.isLoading = false;
    }
  }

  /**
   * Get the appropriate icon for the related record based on model
   * @returns {String} Font Awesome icon class
   */
  getRelatedRecordIcon() {
    if (!this.thread.relatedThreadModel) {
      return "fa-file-o";
    }

    // Common model icons mapping
    const iconMap = {
      "res.partner": "fa-user",
      "res.users": "fa-user",
      "sale.order": "fa-shopping-cart",
      "purchase.order": "fa-shopping-bag",
      "account.move": "fa-file-text-o",
      "project.project": "fa-folder-open",
      "project.task": "fa-check-square-o",
      "helpdesk.ticket": "fa-ticket",
      "crm.lead": "fa-bullseye",
      "hr.employee": "fa-user-circle",
      "product.product": "fa-cube",
      "product.template": "fa-cubes",
      "stock.picking": "fa-truck",
      "mrp.production": "fa-cogs",
      "maintenance.request": "fa-wrench",
    };

    return iconMap[this.thread.relatedThreadModel] || "fa-file-o";
  }

  /**
   * Handle click on related record button
   */
  async onClickRelatedRecord() {
    if (!this.thread.relatedThread) {
      return;
    }

    try {
      await this.env.services.action.doAction({
        type: "ir.actions.act_window",
        res_model: this.thread.relatedThreadModel,
        res_id: this.thread.relatedThreadId,
        views: [[false, "form"]],
        target: "current",
      });
    } catch (error) {
      console.error("Error opening related record:", error);
      this.messaging.notify({
        message: this.env._t("Failed to open related record"),
        type: "danger",
      });
    }
  }

  /**
   * Handle click on choose record button - opens a record picker dialog
   */
  async onClickChooseRecord() {
    try {
      // Get list of available models for the picker
      const models = await this._getAvailableModels();

      if (models.length === 0) {
        this.messaging.notify({
          message: this.env._t("No models available for linking"),
          type: "warning",
        });
        return;
      }

      // Open the record picker dialog
      this._openRecordPickerDialog(models);
    } catch (error) {
      console.error("Error opening record picker:", error);
      this.messaging.notify({
        message: this.env._t("Failed to open record picker"),
        type: "danger",
      });
    }
  }

  /**
   * Handle unlinking the current related record
   */
  async onClickUnlinkRecord() {
    if (!this.thread.relatedThread) {
      return;
    }

    // Show confirmation dialog
    const confirmed = await this._showUnlinkConfirmationDialog();
    if (!confirmed) {
      return;
    }

    try {
      // Use direct RPC call to update the thread instead of updateLLMChatThreadSettings
      await this.messaging.rpc({
        model: "llm.thread",
        method: "write",
        args: [
          [this.thread.id],
          {
            model: false,
            res_id: false,
          },
        ],
      });

      // Refresh the thread to get updated data
      if (this.thread.llmChat) {
        await this.thread.llmChat.refreshThread(this.thread.id);
      }

      // Update local state for immediate UI feedback
      this.thread.update({
        relatedThreadModel: null,
        relatedThreadId: null,
      });

      // Clear the display name
      this.state.relatedRecordDisplayName = "";

      this.messaging.notify({
        message: this.env._t("Record unlinked successfully"),
        type: "success",
      });
    } catch (error) {
      console.error("Error unlinking record:", error);
      this.messaging.notify({
        message: this.env._t("Failed to unlink record"),
        type: "danger",
      });
    }
  }

  // --------------------------------------------------------------------------
  // Private Methods
  // --------------------------------------------------------------------------

  /**
   * Get available models that can be linked to threads
   * @private
   */
  async _getAvailableModels() {
    try {
      const result = await this.messaging.rpc({
        model: "ir.model",
        method: "search_read",
        kwargs: {
          domain: [
            ["transient", "=", false],
            [
              "model",
              "not in",
              ["mail.message", "mail.followers", "ir.attachment"],
            ],
            ["access_ids", "!=", false], // Only models with access rights
          ],
          fields: ["model", "name"],
          order: "name",
          limit: 100, // Reasonable limit for common models
        },
      });

      // Filter to common business models for better UX
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

      result.forEach((model) => {
        if (commonModels.includes(model.model)) {
          prioritizedModels.push(model);
        } else {
          otherModels.push(model);
        }
      });

      // Sort prioritized models by their order in commonModels array
      prioritizedModels.sort((a, b) => {
        const indexA = commonModels.indexOf(a.model);
        const indexB = commonModels.indexOf(b.model);
        return indexA - indexB;
      });

      return [...prioritizedModels, ...otherModels];
    } catch (error) {
      console.error("Error fetching available models:", error);
      return [];
    }
  }

  /**
   * Open the record picker dialog
   * @private
   * @param {Array} models - Available models to choose from
   */
  _openRecordPickerDialog(models) {
    // Create modal HTML
    const modalId = `recordPickerModal_${Date.now()}`;
    const modalHtml = this._createRecordPickerModalHtml(modalId, models);

    // Add modal to DOM
    document.body.insertAdjacentHTML("beforeend", modalHtml);
    const modalElement = document.getElementById(modalId);

    // Initialize Bootstrap modal
    const $modal = $(modalElement);
    const modal = {
      show: () => $modal.modal("show"),
      hide: () => $modal.modal("hide"),
    };

    // Setup event handlers - CRITICAL: Bind 'this' context
    this._setupRecordPickerEventHandlers(modalElement, modal);

    // Show modal
    modal.show();

    // Cleanup when modal is hidden
    modalElement.addEventListener("hidden.bs.modal", () => {
      modalElement.remove();
    });
  }

  /**
   * Create the HTML for the record picker modal
   * @private
   * @param {String} modalId - Unique modal ID
   * @param {Array} models - Available models
   * @returns {String} Modal HTML
   */
  _createRecordPickerModalHtml(modalId, models) {
    const modelOptions = models
      .map((model) => `<option value="${model.model}">${model.name}</option>`)
      .join("");

    return `
      <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-lg">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">
                <i class="fa fa-link me-2"></i>Link Record to Chat
              </h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <!-- Step 1: Model Selection -->
              <div class="step-1">
                <div class="mb-3">
                  <label class="form-label fw-bold">1. Choose Record Type</label>
                  <select class="form-select model-select">
                    <option value="">Select a record type...</option>
                    ${modelOptions}
                  </select>
                </div>
              </div>

              <!-- Step 2: Record Selection -->
              <div class="step-2" style="display: none;">
                <div class="mb-3">
                  <label class="form-label fw-bold">2. Search and Select Record</label>
                  <div class="input-group mb-2">
                    <input type="text" class="form-control record-search"
                           placeholder="Type to search records...">
                    <button class="btn btn-outline-secondary search-btn" type="button">
                      <i class="fa fa-search"></i>
                    </button>
                  </div>

                  <!-- Search Results -->
                  <div class="record-results" style="max-height: 300px; overflow-y: auto;">
                    <div class="text-muted text-center p-3 no-results">
                      <i class="fa fa-search fa-2x mb-2"></i>
                      <p>Search for records above</p>
                    </div>
                  </div>

                  <!-- Loading State -->
                  <div class="loading-state text-center p-3" style="display: none;">
                    <div class="spinner-border spinner-border-sm me-2"></div>
                    Searching...
                  </div>
                </div>
              </div>

              <!-- Selected Record Preview -->
              <div class="selected-record alert alert-info" style="display: none;">
                <h6 class="alert-heading">
                  <i class="fa fa-check-circle me-2"></i>Selected Record
                </h6>
                <div class="selected-record-info"></div>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                Cancel
              </button>
              <button type="button" class="btn btn-primary link-btn" disabled>
                <i class="fa fa-link me-2"></i>Link to Chat
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Setup event handlers for the record picker modal
   * @private
   * @param {HTMLElement} modalElement - Modal DOM element
   * @param {bootstrap.Modal} modal - Bootstrap modal instance
   */
  _setupRecordPickerEventHandlers(modalElement, modal) {
    const modelSelect = modalElement.querySelector(".model-select");
    const step2 = modalElement.querySelector(".step-2");
    const recordSearch = modalElement.querySelector(".record-search");
    const searchBtn = modalElement.querySelector(".search-btn");
    const recordResults = modalElement.querySelector(".record-results");
    const loadingState = modalElement.querySelector(".loading-state");
    const selectedRecord = modalElement.querySelector(".selected-record");
    const selectedRecordInfo = modalElement.querySelector(
      ".selected-record-info"
    );
    const linkBtn = modalElement.querySelector(".link-btn");

    let selectedModel = "";
    let selectedRecordId = null;
    let searchTimeout = null;

    // Helper functions
    const clearRecordSelection = () => {
      selectedRecordId = null;
      selectedRecord.style.display = "none";
      linkBtn.disabled = true;
      recordResults.innerHTML = `
        <div class="text-muted text-center p-3 no-results">
          <i class="fa fa-search fa-2x mb-2"></i>
          <p>Search for records above</p>
        </div>
      `;
    };

    const selectRecord = (recordId, recordName, recordModel) => {
      selectedRecordId = recordId;
      selectedRecordInfo.innerHTML = `
        <strong>${recordName}</strong><br>
        <small class="text-muted">${recordModel} #${recordId}</small>
      `;
      selectedRecord.style.display = "block";
      linkBtn.disabled = false;
    };

    // Model selection handler
    modelSelect.addEventListener("change", (e) => {
      selectedModel = e.target.value;
      if (selectedModel) {
        step2.style.display = "block";
        recordSearch.focus();
        clearRecordSelection();
      } else {
        step2.style.display = "none";
        clearRecordSelection();
      }
    });

    // Search input handler with debouncing
    recordSearch.addEventListener("input", (e) => {
      const query = e.target.value.trim();

      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        if (query.length >= 2) {
          this._searchRecords(
            selectedModel,
            query,
            recordResults,
            loadingState
          );
        } else {
          this._showNoResults(recordResults);
        }
      }, 300);
    });

    // Search button handler
    searchBtn.addEventListener("click", () => {
      const query = recordSearch.value.trim();
      if (query.length >= 2) {
        this._searchRecords(selectedModel, query, recordResults, loadingState);
      }
    });

    // Enter key in search input
    recordSearch.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        searchBtn.click();
      }
    });

    // Link button handler
    linkBtn.addEventListener("click", async () => {
      if (selectedRecordId) {
        try {
          await this._linkRecordToThread(selectedModel, selectedRecordId);
          modal.hide();
          this.messaging.notify({
            message: this.env._t("Record linked successfully"),
            type: "success",
          });
          // Reload the display name
          await this._loadRelatedRecordDisplayName();
        } catch (error) {
          console.error("Error linking record:", error);
          this.messaging.notify({
            message: this.env._t("Failed to link record"),
            type: "danger",
          });
        }
      }
    });

    // Store helper functions for use in search methods
    this._clearRecordSelection = clearRecordSelection;
    this._selectRecord = selectRecord;
  }

  /**
   * Search for records of the specified model
   * @private
   * @param {String} model - Model name to search
   * @param {String} query - Search query
   * @param {HTMLElement} resultsContainer - Container for results
   * @param {HTMLElement} loadingContainer - Loading indicator container
   */
  async _searchRecords(model, query, resultsContainer, loadingContainer) {
    // Show loading state
    resultsContainer.style.display = "none";
    loadingContainer.style.display = "block";

    try {
      const result = await this.messaging.rpc({
        model: model,
        method: "name_search",
        kwargs: {
          name: query,
          limit: 20,
        },
      });

      // Hide loading state
      loadingContainer.style.display = "none";
      resultsContainer.style.display = "block";

      if (result.length === 0) {
        this._showNoResults(resultsContainer, query);
        return;
      }

      // Render results
      const resultsHtml = result
        .map(
          ([id, name]) => `
        <div class="record-item list-group-item list-group-item-action d-flex justify-content-between align-items-center"
             data-record-id="${id}" data-record-name="${name}" data-record-model="${model}"
             style="cursor: pointer;">
          <div>
            <div class="fw-medium">${name}</div>
            <small class="text-muted">${model} #${id}</small>
          </div>
          <i class="fa fa-chevron-right text-muted"></i>
        </div>
      `
        )
        .join("");

      resultsContainer.innerHTML = `<div class="list-group">${resultsHtml}</div>`;

      // Add click handlers for record selection
      resultsContainer.querySelectorAll(".record-item").forEach((item) => {
        item.addEventListener("click", () => {
          // Remove previous selection
          resultsContainer
            .querySelectorAll(".record-item")
            .forEach((i) => i.classList.remove("active"));

          // Add selection to clicked item
          item.classList.add("active");

          // Update selection
          const recordId = parseInt(item.dataset.recordId);
          const recordName = item.dataset.recordName;
          const recordModel = item.dataset.recordModel;

          this._selectRecord(recordId, recordName, recordModel);
        });
      });
    } catch (error) {
      console.error("Error searching records:", error);
      loadingContainer.style.display = "none";
      resultsContainer.style.display = "block";
      resultsContainer.innerHTML = `
        <div class="alert alert-danger">
          <i class="fa fa-exclamation-triangle me-2"></i>
          Error searching records. Please try again.
        </div>
      `;
    }
  }

  /**
   * Show no results message
   * @private
   * @param {HTMLElement} container - Results container
   * @param {String} query - Search query (optional)
   */
  _showNoResults(container, query = "") {
    const message = query
      ? `No records found for "${query}"`
      : "Search for records above";

    container.innerHTML = `
      <div class="text-muted text-center p-3">
        <i class="fa fa-search fa-2x mb-2"></i>
        <p>${message}</p>
      </div>
    `;
  }

  /**
   * Link the selected record to the current thread
   * @private
   * @param {String} model - Record model
   * @param {Number} recordId - Record ID
   */
  async _linkRecordToThread(model, recordId) {
    // Use direct RPC call to update the thread instead of updateLLMChatThreadSettings
    await this.messaging.rpc({
      model: "llm.thread",
      method: "write",
      args: [
        [this.thread.id],
        {
          model: model,
          res_id: recordId,
        },
      ],
    });

    // Refresh the thread to get updated data
    if (this.thread.llmChat) {
      await this.thread.llmChat.refreshThread(this.thread.id);
    }

    // Update local state for immediate UI feedback
    this.thread.update({
      relatedThreadModel: model,
      relatedThreadId: recordId,
    });
  }

  /**
   * Show confirmation dialog for unlinking record
   * @private
   * @returns {Promise<Boolean>} True if confirmed, false otherwise
   */
  async _showUnlinkConfirmationDialog() {
    return new Promise((resolve) => {
      const modalId = `unlinkConfirmModal_${Date.now()}`;
      const recordName =
        this.relatedRecordDisplayName ||
        `${this.thread.relatedThreadModel} #${this.thread.relatedThreadId}`;

      const modalHtml = `
        <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
          <div class="modal-dialog">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title">
                  <i class="fa fa-unlink me-2 text-warning"></i>Unlink Record
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
              </div>
              <div class="modal-body">
                <div class="d-flex align-items-start">
                  <i class="fa fa-exclamation-triangle fa-2x text-warning me-3 mt-1"></i>
                  <div>
                    <h6 class="mb-2">Are you sure you want to unlink this record?</h6>
                    <p class="mb-2">
                      <strong>${recordName}</strong> will no longer be associated with this chat thread.
                    </p>
                    <p class="text-muted small mb-0">
                      This action won't delete the record itself, only remove the link to this chat.
                    </p>
                  </div>
                </div>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary cancel-btn" data-bs-dismiss="modal">
                  Cancel
                </button>
                <button type="button" class="btn btn-warning confirm-btn">
                  <i class="fa fa-unlink me-2"></i>Unlink Record
                </button>
              </div>
            </div>
          </div>
        </div>
      `;

      // Add modal to DOM
      document.body.insertAdjacentHTML("beforeend", modalHtml);
      const modalElement = document.getElementById(modalId);

      // Initialize Bootstrap modal
      const $modal = $(modalElement);
      const modal = {
        show: () => $modal.modal("show"),
        hide: () => $modal.modal("hide"),
      };

      // Setup event handlers
      const confirmBtn = modalElement.querySelector(".confirm-btn");
      const cancelBtn = modalElement.querySelector(".cancel-btn");

      confirmBtn.addEventListener("click", () => {
        modal.hide();
        resolve(true);
      });

      // Cancel/close handlers
      [cancelBtn, modalElement.querySelector(".btn-close")].forEach((btn) => {
        if (btn) {
          btn.addEventListener("click", () => {
            modal.hide();
            resolve(false);
          });
        }
      });

      // Handle modal close by clicking outside or pressing Escape
      modalElement.addEventListener("hidden.bs.modal", () => {
        modalElement.remove();
        resolve(false);
      });

      // Show modal
      modal.show();
    });
  }
}

Object.assign(LLMChatThreadRelatedRecord, {
  props: {
    thread: Object,
  },
  template: "llm_thread.LLMChatThreadRelatedRecord",
});

registerMessagingComponent(LLMChatThreadRelatedRecord);
