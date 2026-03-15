/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useEffect, useRef, useState } from "@odoo/owl";
import { JsonEditorComponent } from "@web_json_editor/components/json_editor/json_editor";
import { LLMFormFieldsView } from "./llm_form_fields_view";
import { useService } from "@web/core/utils/hooks";

export class LLMMediaForm extends Component {
  setup() {
    this.orm = useService("orm");
    this.llmStore = useState(useService("llm.store"));
    this.mailStore = useState(useService("mail.store"));
    this.attachmentInputRef = useRef("attachmentInput");

    this.state = useState({
      formValues: {},
      isLoading: false,
      error: null,
      showAdvancedSettings: false,
      inputMode: "form",
      isJsonValid: true,
      jsonEditorError: null,
      hasSchemaValidationErrors: false,
      showTemplatePreview: false,
      templatePreviewContent: null,
      isLoadingPreview: false,
      assistantDefaults: {},
      threadConfig: {
        input_schema: {},
        form_defaults: {},
      },
      attachments: [],
      uploadingFiles: false,
      schemaSource: { type: "loading", name: _t("Loading...") },
    });

    onWillStart(async () => {
      this.state.isLoading = true;
      try {
        await this._loadThreadConfiguration();
        this._initializeFormValues();
      } finally {
        this.state.isLoading = false;
      }
    });

    // Watch for changes in the model/thread context
    useEffect(
      () => {
        this._handleContextChange();
      },
      () => [
        this.props.threadId,
        this.thread?.model_id,
        this.thread?.assistant_id,
      ]
    );

    // Compute schema source when prompt_id changes
    useEffect(
      () => {
        this._computeSchemaSource();
      },
      () => [
        this.thread?.prompt_id,
        this.thread?.assistant_id,
        this.state.threadConfig.input_schema,
        this.llmModel,
      ]
    );
  }

  get thread() {
    // Get thread from mailStore using thread ID from props
    const threadId = this.props.threadId;
    if (!threadId) return null;

    return this.mailStore.Thread.get({ model: "llm.thread", id: threadId });
  }

  get llmModel() {
    const modelId = this.thread?.model_id?.id || this.thread?.model_id;
    if (!modelId) return null;

    return this.llmStore.llmModels[modelId];
  }

  get composer() {
    // Get composer from thread
    return this.thread?.composer;
  }

  /**
   * Load thread configuration (schema + defaults) from backend
   */
  async _loadThreadConfiguration() {
    const threadId = this.props.threadId;
    if (!threadId) {
      return;
    }

    this.state.isLoading = true;
    try {
      const config = await this.orm.call(
        "llm.thread",
        "get_generation_form_config",
        [threadId]
      );
      this.state.threadConfig = config;

      if (config.error) {
        this.state.error = config.error;
      } else {
        this.state.error = null;
      }
    } catch (error) {
      console.error("Error loading thread configuration:", error);
      this.state.error = _t("Failed to load thread configuration");
    } finally {
      this.state.isLoading = false;
    }
  }

  /**
   * Handle context changes (prompt, assistant, etc.)
   */
  async _handleContextChange() {
    this.state.isLoading = true;
    try {
      await this._loadThreadConfiguration();
      this._initializeFormValues();
    } finally {
      this.state.isLoading = false;
    }
  }

  get inputSchema() {
    // Return empty schema during loading to prevent race conditions
    if (this.state.isLoading) {
      return {};
    }

    // First try to get from thread config (includes prompt and assistant processing)
    let schema = this.state.threadConfig.input_schema;

    // If no thread config schema, try model's schema
    if (!schema || Object.keys(schema).length === 0) {
      schema = this.llmModel?.inputSchema;
    }

    if (!schema || typeof schema !== "object") {
      console.warn("No input schema found for model:", this.llmModel?.name);
      // Return empty object instead of null
      return {};
    }

    let parsedSchema = null;
    if (typeof schema === "string") {
      try {
        parsedSchema = JSON.parse(schema);
      } catch (e) {
        console.error("Error parsing input schema:", e);
        // Return empty object instead of null
        return {};
      }
    } else {
      parsedSchema = schema;
    }

    // Normalize the schema to fix JSON Schema compliance issues
    const normalizedSchema = this._normalizeSchema(parsedSchema);

    return normalizedSchema;
  }

  /**
   * Normalize schema to fix field-level required issue
   * @param {Object} schema - JSON schema to normalize
   * @returns {Object} Normalized schema
   */
  _normalizeSchema(schema) {
    if (!schema || typeof schema !== "object") {
      return schema;
    }

    // Clone the schema to avoid modifying the original
    const normalizedSchema = JSON.parse(JSON.stringify(schema));

    // Ensure we have a proper schema structure
    if (!normalizedSchema.type) {
      normalizedSchema.type = "object";
    }

    if (!normalizedSchema.properties) {
      return normalizedSchema;
    }

    // Collect required fields from individual property definitions
    const requiredFields = [];

    // Process each property
    Object.entries(normalizedSchema.properties).forEach(
      ([fieldName, fieldDef]) => {
        // Move field-level required to schema-level required array
        if (fieldDef.required === true) {
          requiredFields.push(fieldName);
          // Remove invalid field-level required
          delete fieldDef.required;
        }
      }
    );

    // Merge with existing required array if present
    if (Array.isArray(normalizedSchema.required)) {
      requiredFields.forEach((field) => {
        if (!normalizedSchema.required.includes(field)) {
          normalizedSchema.required.push(field);
        }
      });
    } else if (requiredFields.length > 0) {
      normalizedSchema.required = requiredFields;
    }

    return normalizedSchema;
  }

  get formFields() {
    // Return empty array during loading to prevent race conditions
    if (this.state.isLoading) {
      return [];
    }

    const inputSchema = this.inputSchema;

    if (!inputSchema?.properties) {
      return [];
    }

    // Extract required fields array
    const requiredFields = Array.isArray(inputSchema.required)
      ? inputSchema.required
      : [];

    // Convert properties object to array of field definitions
    return Object.entries(inputSchema.properties)
      .map(([name, fieldDef]) => {
        // Check if field name is 'prompt' (case insensitive)
        const isPromptField = name.toLowerCase() === "prompt";

        // Handle enum types
        let choices = null;
        let fieldType = fieldDef.type;

        if (fieldDef.allOf?.[0]?.enum) {
          choices = fieldDef.allOf[0].enum.map((item) => ({
            value: item,
            label: typeof item === "object" ? item.label || item.value : item,
          }));
          fieldType = "enum";
        } else if (fieldDef.enum) {
          choices = fieldDef.enum.map((item) => ({
            value: item,
            label: typeof item === "object" ? item.label || item.value : item,
          }));
          fieldType = "enum";
        }

        return {
          name: name,
          label:
            fieldDef.title ||
            name.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
          type: fieldType,
          required: isPromptField || requiredFields.includes(name),
          description: fieldDef.description,
          default: fieldDef.default,
          choices: choices,
          minimum: fieldDef.minimum,
          maximum: fieldDef.maximum,
          format: fieldDef.format,
          order: fieldDef["x-order"] ?? 999,
        };
      })
      .sort((a, b) => a.order - b.order);
  }

  get requiredFields() {
    return this.formFields.filter((field) => field.required);
  }

  get optionalFields() {
    return this.formFields.filter((field) => !field.required);
  }

  /**
   * Compute schema source information - called when dependencies change
   */
  _computeSchemaSource() {
    if (this.state.isLoading) {
      this.state.schemaSource = { type: "loading", name: _t("Loading...") };
      return;
    }

    // Check if thread has a prompt_id - if so, schema is from prompt
    const hasPrompt = Boolean(this.thread?.prompt_id);
    const hasSchema =
      this.state.threadConfig.input_schema &&
      Object.keys(this.state.threadConfig.input_schema).length > 0;

    if (hasSchema) {
      if (hasPrompt) {
        // Schema exists AND prompt is set -> schema is from prompt
        this.state.schemaSource = {
          type: "prompt",
          name: this.thread?.prompt_id?.name || _t("Selected Prompt"),
        };
      } else {
        // Schema exists but NO prompt -> schema must be from model
        this.state.schemaSource = {
          type: "model",
          name: this.llmModel?.name || _t("Model Default"),
        };
      }
      return;
    }

    this.state.schemaSource = { type: "none", name: _t("No Schema Available") };
  }

  /**
   * Get schema source from state (for template access)
   */
  get schemaSource() {
    return this.state.schemaSource;
  }

  /**
   * Initialize form values with defaults from thread configuration
   */
  _initializeFormValues() {
    // Don't initialize during loading to prevent race conditions
    if (this.state.isLoading) {
      return;
    }

    const defaults = this.state.threadConfig.form_defaults || {};

    // Start with schema defaults
    const initialValues = {};
    this.formFields.forEach((field) => {
      if (field.default !== undefined) {
        initialValues[field.name] = field.default;
      }
    });

    // Apply thread defaults (these take precedence over schema defaults)
    Object.assign(initialValues, defaults);

    // Set assistant defaults for display
    this.state.assistantDefaults = defaults || {};

    this.state.formValues = initialValues;
  }

  /**
   * Toggle template preview visibility and load preview content
   */
  async toggleTemplatePreview() {
    this.state.showTemplatePreview = !this.state.showTemplatePreview;

    if (this.state.showTemplatePreview) {
      await this._loadTemplatePreview();
    }
  }

  /**
   * Load template preview by calling the backend to render the prompt
   */
  async _loadTemplatePreview() {
    const threadId = this.props.threadId;
    if (!threadId) {
      this.state.templatePreviewContent =
        "No thread available for template preview";
      return;
    }

    this.state.isLoadingPreview = true;
    try {
      // Merge defaults with current form values (same logic as submission)
      const mergedInputs = {
        ...this.state.assistantDefaults,
        ...this.state.formValues,
      };

      // Call backend method to prepare generation inputs (which handles template rendering)
      const result = await this.orm.call(
        "llm.thread",
        "prepare_generation_inputs",
        [threadId, mergedInputs]
      );

      // Display the result based on its type
      if (typeof result === "string") {
        this.state.templatePreviewContent = result;
      } else if (typeof result === "object") {
        this.state.templatePreviewContent = JSON.stringify(result, null, 2);
      } else {
        this.state.templatePreviewContent = String(result);
      }
    } catch (error) {
      console.error("Error loading template preview:", error);
      this.state.templatePreviewContent = `Error loading preview: ${error.message}`;
    } finally {
      this.state.isLoadingPreview = false;
    }
  }

  /**
   * Get formatted template preview
   */
  get formattedTemplatePreview() {
    return this.state.templatePreviewContent || _t("Loading preview...");
  }

  /**
   * Toggle input mode between form and JSON editor
   */
  toggleInputMode() {
    this.state.inputMode = this.state.inputMode === "form" ? "json" : "form";
    this.state.jsonEditorError = null;
    this.state.hasSchemaValidationErrors = false;
  }

  /**
   * Handler for JSON editor changes
   */
  onJsonEditorChange({ value, isValid, error }) {
    this.state.isJsonValid = isValid;

    if (isValid) {
      this.state.formValues = value;
      // Only clear errors if we don't have schema validation errors pending
      if (!this.state.hasSchemaValidationErrors) {
        this.state.jsonEditorError = null;
      }
    } else if (!this.state.hasSchemaValidationErrors) {
      // Only set syntax errors if we don't have schema validation errors
      this.state.jsonEditorError = error || "Invalid JSON format.";
    }
  }

  /**
   * Handle JSON validation errors
   * @param {Array} errors - Validation errors from JSON schema
   */
  onJsonValidationError(errors) {
    if (errors?.length > 0) {
      const formattedErrors = errors.map((error) => {
        const path = error.path ? error.path.join(".") : "";
        return `${path ? path + ": " : ""}${error.message}`;
      });
      this.state.jsonEditorError = formattedErrors.join("\n");
      this.state.hasSchemaValidationErrors = true;
      this.state.isJsonValid = false;
    } else {
      this.state.hasSchemaValidationErrors = false;
      // Only clear errors if JSON is also syntactically valid
      if (this.state.isJsonValid) {
        this.state.jsonEditorError = null;
      }
    }
  }

  /**
   * Handle general JSON editor errors
   * @param {Object} error - Error object from JSON editor
   */
  onJsonEditorError(error) {
    console.error("JSON Editor Error:", error);
    this.state.jsonEditorError =
      error.message || "An error occurred in the JSON editor.";
  }

  /**
   * Toggle advanced settings visibility
   */
  toggleAdvancedSettings() {
    this.state.showAdvancedSettings = !this.state.showAdvancedSettings;
  }

  /**
   * Handle form input changes
   * @param {String} fieldName - Name of the field being changed
   * @param {Event} event - Input change event
   */
  onInputChange(fieldName, event) {
    const target = event.target;
    let value = null;

    const fieldDef = this.formFields.find((field) => field.name === fieldName);

    if (target.type === "checkbox") {
      value = target.checked;
    } else if (target.type === "number" || target.type === "range") {
      value = parseFloat(target.value);
    } else if (fieldDef?.type === "integer") {
      value = parseInt(target.value, 10);
    } else {
      value = target.value;
    }

    this.state.formValues = {
      ...this.state.formValues,
      [fieldName]: value,
    };

    // If template preview is open, refresh it with the new values
    if (this.state.showTemplatePreview) {
      this._loadTemplatePreview();
    }
  }

  /**
   * Validate and convert field value based on type
   * @param {*} value - Field value to validate
   * @param {Object} schemaField - Schema field definition
   * @param {String} label - Field label for error messages
   * @returns {Object} Object with processedValue and error (if any)
   */
  _validateFieldValue(value, schemaField, label) {
    let processedValue = value;
    let error = null;

    switch (schemaField.type) {
      case "integer": {
        const intValue = parseFloat(value);
        if (isNaN(intValue) || !Number.isInteger(intValue)) {
          error = `Field "${label}" must be an integer.`;
        } else {
          processedValue = intValue;
        }
        break;
      }
      case "number": {
        const floatValue = parseFloat(value);
        if (isNaN(floatValue)) {
          error = `Field "${label}" must be a number.`;
        } else {
          processedValue = floatValue;
        }
        break;
      }
      case "boolean":
        if (typeof value === "string") {
          processedValue = value.toLowerCase() === "true";
        } else if (typeof value !== "boolean") {
          error = `Field "${label}" must be a boolean.`;
        }
        break;
      case "string":
        if (value !== null && value !== undefined) {
          processedValue = String(value);
        }
        break;
    }

    return { processedValue, error };
  }

  /**
   * Validate form values against schema
   * @returns {Object} Object with errors array and validatedValues
   */
  _validateFormValues() {
    const errors = [];
    const validatedValues = {};

    for (const schemaField of this.formFields) {
      const fieldName = schemaField.name;
      const label = schemaField.label || fieldName;
      const value = this.state.formValues[fieldName];

      // Check required fields
      if (schemaField.required) {
        const isMissingOrEmpty =
          value === undefined ||
          value === null ||
          (typeof value === "string" && value.trim() === "");

        if (isMissingOrEmpty) {
          errors.push(`Field "${label}" is required.`);
          continue;
        }
      }

      // Validate and convert types
      if (value !== undefined) {
        const result = this._validateFieldValue(value, schemaField, label);
        if (result.error) {
          errors.push(result.error);
        }
        validatedValues[fieldName] = result.processedValue;
      }
    }

    return {
      isValid: errors.length === 0,
      errors: errors,
      values: errors.length === 0 ? validatedValues : this.state.formValues,
    };
  }

  /**
   * Handle form submission
   * @param {Event} event - Form submit event
   */
  async onSubmit(event) {
    event.preventDefault();

    const validationResult = this._validateFormValues();

    if (!validationResult.isValid) {
      this.state.error = validationResult.errors.join("\n");
      return;
    }

    // Check if model supports generation
    const modelUse = this.llmModel?.model_use;
    if (modelUse !== "generation" && modelUse !== "image_generation") {
      this.state.error = "Selected model is not configured for generation.";
      return;
    }

    const threadId = this.props.threadId;
    if (!threadId) {
      this.state.error = "Thread not available.";
      return;
    }

    this.state.isLoading = true;
    this.state.error = null;

    try {
      // Submit through llmStore - uses body_json and includes attachments
      await this.llmStore.postGenerationMessage(
        threadId,
        validationResult.values,
        this.state.attachments
      );

      // Clear attachments after successful submission
      this.state.attachments = [];
    } catch (error) {
      console.error("Error submitting generation form:", error);
      this.state.error =
        error.message || "An unexpected error occurred during submission.";
    } finally {
      this.state.isLoading = false;
    }
  }

  /**
   * Check if streaming is active
   * @returns {Boolean} True if streaming is active
   */
  isStreaming() {
    const threadId = this.props.threadId;
    return this.llmStore.isStreamingThread(threadId) || false;
  }

  /**
   * Handle file attachment changes
   * @param {Event} event - File input change event
   */
  async onAttachmentChange(event) {
    const files = Array.from(event.target.files);
    if (!files.length) return;

    this.state.uploadingFiles = true;

    try {
      for (const file of files) {
        // Use Odoo's ORM to create attachment record directly
        const fileDataUrl = await this._readFileAsDataURL(file);
        // Remove data:mime/type;base64, prefix
        const base64Data = fileDataUrl.split(",")[1];

        const attachmentIds = await this.orm.create("ir.attachment", [
          {
            name: file.name,
            datas: base64Data,
            res_model: "mail.compose.message",
            // Temporary attachment
            res_id: 0,
            mimetype: file.type,
          },
        ]);

        // Orm.create with array returns array of IDs, extract first element
        if (attachmentIds && attachmentIds.length > 0) {
          this.state.attachments.push({
            // Get first ID from array
            id: attachmentIds[0],
            name: file.name,
            size: file.size,
            mimetype: file.type,
          });
        }
      }
    } catch (error) {
      console.error("Error uploading attachments:", error);
      this.state.error = _t("Failed to upload one or more attachments.");
    } finally {
      this.state.uploadingFiles = false;
      // Clear the input to allow re-selecting the same files
      if (this.attachmentInputRef.el) {
        this.attachmentInputRef.el.value = "";
      }
    }
  }

  /**
   * Read file as data URL
   * @param {File} file - File to read
   * @returns {Promise<String>} Promise resolving to data URL
   */
  _readFileAsDataURL(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  /**
   * Remove an attachment from the list
   * @param {Object} attachment - Attachment to remove
   */
  removeAttachment(attachment) {
    const index = this.state.attachments.findIndex(
      (a) => a.id === attachment.id || a.name === attachment.name
    );
    if (index !== -1) {
      this.state.attachments.splice(index, 1);
    }
  }

  /**
   * Format file size for display
   * @param {Number} bytes - File size in bytes
   * @returns {String} Formatted file size string
   */
  formatFileSize(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }
}

LLMMediaForm.props = {
  threadId: { type: Number, optional: false },
};

LLMMediaForm.template = "llm_thread.LLMMediaForm";
LLMMediaForm.components = { JsonEditorComponent, LLMFormFieldsView };
