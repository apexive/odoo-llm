/** @odoo-module **/

import { registerMessagingComponent } from "@mail/utils/messaging_component";
import { JsonEditorComponent } from "@web_json_editor/components/json_editor/json_editor";
import { LLMFormFieldsView } from "./llm_form_fields_view";
const { Component, useState, onWillStart, useEffect } = owl;

export class LLMMediaForm extends Component {
  setup() {
    this.state = useState({
      formValues: {},
      isLoading: false,
      error: null,
      showAdvancedSettings: false,
      inputMode: "form",
      isJsonValid: true,
      jsonEditorError: null,
      showTemplatePreview: false,
      templatePreviewContent: null,
      isLoadingPreview: false,
      assistantDefaults: {},
      threadConfig: {
        input_schema: {},
        form_defaults: {},
      },
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
        this.thread?.id,
        this.llmAssistant?.id,
        this.thread?.prompt_id?.id,
        this.llmModel?.id,
      ]
    );
  }

  get thread() {
    return this.props.model;
  }

  get llmModel() {
    return this.thread?.llmModel;
  }

  get llmAssistant() {
    return this.thread?.llmAssistant;
  }

  get llmChat() {
    return this.thread?.llmChat;
  }

  /**
   * Load thread configuration (schema + defaults) from backend
   */
  async _loadThreadConfiguration() {
    if (!this.thread?.id) {
      return;
    }

    this.state.isLoading = true;
    try {
      const config = await this.llmChat.getThreadFormConfiguration();
      this.state.threadConfig = config;

      if (config.error) {
        this.state.error = config.error;
      }
    } catch (error) {
      console.error("Error loading thread configuration:", error);
      this.state.error = "Failed to load thread configuration";
    } finally {
      this.state.isLoading = false;
    }
  }

  /**
   * Handle context changes (prompt, assistant, etc.)
   */
  async _handleContextChange() {
    console.log("Media form context changed, reloading...");
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
      return {}; // Return empty object instead of null
    }

    let parsedSchema;
    if (typeof schema === "string") {
      try {
        parsedSchema = JSON.parse(schema);
      } catch (e) {
        console.error("Error parsing input schema:", e);
        return {}; // Return empty object instead of null
      }
    } else {
      parsedSchema = schema;
    }

    // Normalize the schema to fix JSON Schema compliance issues
    const normalizedSchema = this._normalizeSchema(parsedSchema);
    console.log("Normalized schema:", normalizedSchema);

    return normalizedSchema;
  }

  /**
   * Normalize schema to fix field-level required issue
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
          delete fieldDef.required; // Remove invalid field-level required
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
        let choices;
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
   * Get information about the schema source for transparency
   */
  get schemaSource() {
    if (this.state.isLoading) {
      return { type: 'loading', name: 'Loading...' };
    }

    if (this.state.threadConfig.input_schema && 
        Object.keys(this.state.threadConfig.input_schema).length > 0) {
      return {
        type: 'prompt',
        name: this.thread?.prompt_id?.name || this.llmAssistant?.prompt_id?.name || 'Selected Prompt'
      };
    }
    
    if (this.llmModel?.inputSchema && 
        Object.keys(this.llmModel.inputSchema).length > 0) {
      return {
        type: 'model',
        name: this.llmModel?.name || 'Model Default'
      };
    }

    return { type: 'none', name: 'No Schema Available' };
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
    console.log("Initialized form values:", initialValues);
    console.log("Schema source:", this.schemaSource);
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
    if (!this.thread?.id) {
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
      const result = await this.thread.messaging.rpc({
        model: "llm.thread",
        method: "prepare_generation_inputs",
        args: [this.thread.id, mergedInputs],
      });

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
    return this.state.templatePreviewContent || "Loading preview...";
  }

  /**
   * Toggle input mode between form and JSON editor
   */
  toggleInputMode() {
    this.state.inputMode = this.state.inputMode === "form" ? "json" : "form";
    this.state.jsonEditorError = null;
  }

  /**
   * Handler for JSON editor changes
   */
  onJsonEditorChange({ value, isValid, error }) {
    this.state.isJsonValid = isValid;

    if (isValid) {
      this.state.formValues = value;
      this.state.jsonEditorError = null;
    } else {
      this.state.jsonEditorError = error || "Invalid JSON format.";
    }
  }

  /**
   * Handle JSON validation errors
   */
  onJsonValidationError(errors) {
    if (errors?.length > 0) {
      const formattedErrors = errors.map((error) => {
        const path = error.path ? error.path.join(".") : "";
        return `${path ? path + ": " : ""}${error.message}`;
      });
      this.state.jsonEditorError = formattedErrors.join("\n");
    } else {
      this.state.jsonEditorError = null;
    }
  }

  /**
   * Handle general JSON editor errors
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
   */
  onInputChange(fieldName, event) {
    const target = event.target;
    let value;

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
   * Validate form values against schema
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
        let processedValue = value;

        switch (schemaField.type) {
          case "integer":
            const intValue = parseFloat(value);
            if (isNaN(intValue) || !Number.isInteger(intValue)) {
              errors.push(`Field "${label}" must be an integer.`);
            } else {
              processedValue = intValue;
            }
            break;
          case "number":
            const floatValue = parseFloat(value);
            if (isNaN(floatValue)) {
              errors.push(`Field "${label}" must be a number.`);
            } else {
              processedValue = floatValue;
            }
            break;
          case "boolean":
            if (typeof value === "string") {
              processedValue = value.toLowerCase() === "true";
            } else if (typeof value !== "boolean") {
              errors.push(`Field "${label}" must be a boolean.`);
            }
            break;
          case "string":
            if (value !== null && value !== undefined) {
              processedValue = String(value);
            }
            break;
        }

        validatedValues[fieldName] = processedValue;
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
   */
  async onSubmit(event) {
    event.preventDefault();

    const validationResult = this._validateFormValues();

    if (!validationResult.isValid) {
      this.state.error = validationResult.errors.join("\n");
      return;
    }

    if (!this.llmModel?.isMediaGenerationModel) {
      this.state.error = "Selected model is not configured for generation.";
      return;
    }

    if (!this.thread?.composer) {
      this.state.error = "Composer not available.";
      return;
    }

    this.state.isLoading = true;
    this.state.error = null;

    try {
      const composer = this.thread.composer;
      console.log("Submitting generation request:", validationResult.values);

      // Submit through composer - now uses body_json
      composer.postUserGenerationMessageForLLM(validationResult.values);
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
   */
  isStreaming() {
    return this.thread?.composer?.isStreaming || false;
  }
}

LLMMediaForm.props = {
  model: { type: Object, optional: false },
};

LLMMediaForm.template = "llm_thread.LLMMediaForm";
LLMMediaForm.components = { JsonEditorComponent, LLMFormFieldsView };

registerMessagingComponent(LLMMediaForm);
