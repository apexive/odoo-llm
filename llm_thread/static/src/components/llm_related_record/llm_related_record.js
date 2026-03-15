/** @odoo-module **/

import { Component, onMounted, useState } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { RecordPickerDialog } from "./llm_record_picker_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/**
 * Component for linking Odoo records to LLM chat threads
 *
 * Features:
 * - Display linked record with model-specific icon
 * - Open linked record in form view
 * - Link new records via search picker
 * - Unlink records with confirmation
 * - Responsive design for desktop/mobile
 */
export class LLMRelatedRecord extends Component {
  static template = "llm_thread.LLMRelatedRecord";
  static components = {};
  static props = {
    thread: Object,
  };

  setup() {
    this.state = useState({
      relatedRecordDisplayName: "",
      isLoading: false,
    });

    // Services
    this.orm = useService("orm");
    this.action = useService("action");
    this.dialog = useService("dialog");
    this.ui = useService("ui");
    this.llmStore = useState(useService("llm.store"));

    // Load display name on mount
    onMounted(() => this.loadRelatedRecordDisplayName());
  }

  // -------------------------------------------------------------------------
  // Getters
  // -------------------------------------------------------------------------

  /**
   * Check if thread has a linked record
   * @returns {Boolean}
   */
  get hasRelatedRecord() {
    return Boolean(this.props.thread.res_model && this.props.thread.res_id);
  }

  /**
   * Check if on mobile device
   * @returns {Boolean}
   */
  get isSmall() {
    return this.ui.isSmall;
  }

  // -------------------------------------------------------------------------
  // Display Name Loading
  // -------------------------------------------------------------------------

  /**
   * Load the display name of the linked record
   */
  async loadRelatedRecordDisplayName() {
    if (!this.hasRelatedRecord) {
      this.state.relatedRecordDisplayName = "";
      return;
    }

    try {
      this.state.isLoading = true;
      // Use searchRead instead of name_get (removed in Odoo 18.0)
      const result = await this.orm.searchRead(
        this.props.thread.res_model,
        [["id", "=", this.props.thread.res_id]],
        ["display_name"]
      );

      if (result && result.length > 0) {
        this.state.relatedRecordDisplayName = result[0].display_name;
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
  getRecordIcon() {
    if (!this.props.thread.res_model) {
      return "fa-file-o";
    }

    // Common model icons mapping (from 16.0)
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

    return iconMap[this.props.thread.res_model] || "fa-file-o";
  }

  // -------------------------------------------------------------------------
  // Open Record
  // -------------------------------------------------------------------------

  /**
   * Open the linked record in form view
   */
  async openRelatedRecord() {
    if (!this.hasRelatedRecord) {
      return;
    }

    try {
      await this.action.doAction({
        type: "ir.actions.act_window",
        res_model: this.props.thread.res_model,
        res_id: this.props.thread.res_id,
        views: [[false, "form"]],
        target: "current",
      });
    } catch (error) {
      console.error("Error opening related record:", error);
      this.notification.add(_t("Failed to open related record"), {
        type: "danger",
      });
    }
  }

  // -------------------------------------------------------------------------
  // Link Record
  // -------------------------------------------------------------------------

  /**
   * Open the record picker dialog to link a new record
   */
  openRecordPicker() {
    this.dialog.add(RecordPickerDialog, {
      onConfirm: async (model, recordId) => {
        await this.linkRecord(model, recordId);
      },
    });
  }

  /**
   * Link a record to the current thread
   * @param {String} model - Record model name
   * @param {Number} recordId - Record ID
   */
  async linkRecord(model, recordId) {
    // Delegate to llm.store service for business logic
    const success = await this.llmStore.linkRecordToThread(
      this.props.thread.id,
      model,
      recordId
    );

    if (success) {
      // Reload display name after successful link
      await this.loadRelatedRecordDisplayName();
    }
  }

  // -------------------------------------------------------------------------
  // Unlink Record
  // -------------------------------------------------------------------------

  /**
   * Unlink the current related record with confirmation
   */
  async unlinkRecord() {
    if (!this.hasRelatedRecord) {
      return;
    }

    const recordName =
      this.state.relatedRecordDisplayName ||
      `${this.props.thread.res_model} #${this.props.thread.res_id}`;

    this.dialog.add(ConfirmationDialog, {
      title: _t("Unlink Record"),
      body: _t(
        "Are you sure you want to unlink %s from this chat? " +
          "This won't delete the record, only remove the link.",
        recordName
      ),
      confirm: async () => {
        // Delegate to llm.store service for business logic
        const success = await this.llmStore.unlinkRecordFromThread(
          this.props.thread.id
        );

        if (success) {
          // Clear display name after successful unlink
          this.state.relatedRecordDisplayName = "";
        }
      },
    });
  }
}
