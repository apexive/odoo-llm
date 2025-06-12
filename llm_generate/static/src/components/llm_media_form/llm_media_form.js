/** @odoo-module **/

import { registerMessagingComponent } from "@mail/utils/messaging_component";
import { JsonEditorComponent } from "@web_json_editor/components/json_editor/json_editor";
import { LLMFormFieldsView } from "./llm_form_fields_view";
const { Component, useState, onWillStart, useEffect } = owl;
import { markup } from "@odoo/owl";
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
      supportsAsyncGeneration: false,
    });

    onWillStart(async () => {
      // Initialize form values with defaults after loading config
      this._initializeFormValues();
      // Check if provider supports async generation
      await this._checkAsyncGenerationSupport();
    });

    // Watch for changes in the model prop to reload config if necessary
    useEffect(
      () => {
        this._initializeFormValues();
        this._checkAsyncGenerationSupport();
      },
      // Use thread.id and llmAssistant.id to ensure proper dependency tracking
      () => [this.effectiveInputSchema, this.thread?.id, this.llmAssistant?.id]
    );
  }

  get effectiveInputSchema() {
    if (!this.llmModel || !this.thread) {
      return null;
    }
    // Use the thread-specific schema method
    const schema = this.llmModel.getEffectiveInputSchemaForThread(this.thread);
    return schema;
  }

  // Initialize form values with defaults from schema
  _initializeFormValues() {
    this.state.formValues = {};
    if (!this.formFields || !Array.isArray(this.formFields)) {
      return;
    }

    // Create a new object to hold the initial values
    const initialValues = {};

    // Set default values from schema
    this.formFields.forEach((field) => {
      if (
        this.state.formValues[field.name] === undefined &&
        field.default !== undefined
      ) {
        initialValues[field.name] = field.default;
      } else if (this.state.formValues[field.name] !== undefined) {
        initialValues[field.name] = this.state.formValues[field.name];
      }
    });

    // Update state with initial values
    this.state.formValues = initialValues;
  }
  // Check if provider supports async generation
  async _checkAsyncGenerationSupport() {
    if (!this.thread || !this.thread.provider_id) {
      this.state.supportsAsyncGeneration = false;
      return;
    }

    try {
      const result = await this.env.services.rpc({
        route: '/api/llm/provider/supports_async_generation',
        params: {
          provider_id: this.thread.provider_id,
        },
      });
      this.state.supportsAsyncGeneration = result.supports_async;
    } catch (error) {
      console.warn("Async generation support check failed (llm_generate_job module may not be installed):", error);
      this.state.supportsAsyncGeneration = false;
    }
  }

  get llmModel() {
    return this.thread?.llmModel;
  }

  get thread() {
    return this.props.model;
  }

  get llmAssistant() {
    return this.thread?.llmAssistant;
  }

  get inputSchema() {
    let result = null;
    if (!this.llmModel) {
      result = null;
    } else if (!this.effectiveInputSchema) {
      result = null;
    } else if (typeof this.effectiveInputSchema === "string") {
      result = JSON.parse(this.effectiveInputSchema);
    } else if (typeof this.effectiveInputSchema === "object") {
      result = this.effectiveInputSchema;
    }

    return result;
  }

  get formFields() {
    const inputSchema = this.inputSchema;

    if (!inputSchema) {
      console.warn("LLMMediaForm: inputSchema is not available", inputSchema);
      return [];
    }

    // Check if we have a valid JSON Schema object with properties
    if (!inputSchema.properties || typeof inputSchema.properties !== "object") {
      console.warn(
        "LLMMediaForm: inputSchema doesn't contain properties object",
        inputSchema
      );
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

        // Handle enum types (could be in allOf[0].enum structure)
        let choices;
        let fieldType = fieldDef.type;

        if (fieldDef.allOf && fieldDef.allOf[0] && fieldDef.allOf[0].enum) {
          // Format enum values as objects with value and label properties
          const enumValues = fieldDef.allOf[0].enum;
          choices = enumValues.map((item) => {
            // Check if the enum item is already a {value, label} object
            if (
              item &&
              typeof item === "object" &&
              "value" in item &&
              "label" in item
            ) {
              return item;
            }
            // Otherwise, use the item as both value and label
            return {
              value: item,
              label: item,
            };
          });
          fieldType = "enum";
        } else if (fieldDef.enum) {
          // Handle direct enum property
          const enumValues = fieldDef.enum;
          choices = enumValues.map((item) => {
            // Check if the enum item is already a {value, label} object
            if (
              item &&
              typeof item === "object" &&
              "value" in item &&
              "label" in item
            ) {
              return item;
            }
            // Otherwise, use the item as both value and label
            return {
              value: item,
              label: item,
            };
          });
          fieldType = "enum";
        }

        return {
          name: name,
          label:
            fieldDef.title ||
            name.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
          type: fieldType,
          // Field is required if in required array or if it's the prompt field
          required: isPromptField || requiredFields.includes(name),
          description: this.formatDescription(fieldDef.description),
          default: fieldDef.default,
          choices: choices,
          minimum: fieldDef.minimum,
          maximum: fieldDef.maximum,
          format: fieldDef.format,
          // Use x-order for sorting if available
          order: fieldDef["x-order"] !== undefined ? fieldDef["x-order"] : 999,
        };
      })
      .sort((a, b) => a.order - b.order); // Sort by order field
  }

  // Getter to filter required fields
  get requiredFields() {
    if (!this.formFields || !Array.isArray(this.formFields)) {
      return [];
    }
    return this.formFields.filter((field) => field.required);
  }

  // Getter to filter optional fields
  get optionalFields() {
    if (!this.formFields || !Array.isArray(this.formFields)) {
      return [];
    }
    return this.formFields.filter((field) => !field.required);
  }

  // Toggle input mode between form and JSON editor
  toggleInputMode() {
    if (this.state.inputMode === "form") {
      this.state.inputMode = "json";
    } else {
      // When switching back to form, ensure formValues reflect any valid JSON changes
      // If JSON was invalid, formValues would not have been updated by onJsonEditorChange
      this.state.inputMode = "form";
    }
    this.state.jsonEditorError = null; // Clear any previous JSON errors when toggling
  }

  // Handler for changes from JsonEditorComponent
  onJsonEditorChange({ value, isValid, error, text, validationErrors }) {
    this.state.isJsonValid = isValid;
    if (isValid) {
      this.state.formValues = value; // Value is already a JS object if valid
      this.state.jsonEditorError = null;
    } else {
      // Keep the last valid formValues, but show an error.
      if (validationErrors && validationErrors.length > 0) {
        // We have schema validation errors - these are different from syntax errors
        // If we have a valid JSON object but with schema errors, still update formValues
        if (typeof value === "object" && value !== null) {
          this.state.formValues = value;
        }
        // Error message is already set by onJsonValidationError
      } else {
        // This is a syntax error, not a schema validation error
        this.state.jsonEditorError = error || "Invalid JSON format.";
      }
    }
  }

  // Handle validation errors from schema validation
  onJsonValidationError(errors) {
    if (errors && errors.length > 0) {
      // Format validation errors for display
      const formattedErrors = errors.map((error) => {
        // Format the path in a more readable way
        const path = error.path ? error.path.join(".") : "";
        return `${path ? path + ": " : ""}${error.message}`;
      });

      this.state.jsonEditorError = formattedErrors.join("\n");
    } else {
      this.state.jsonEditorError = null;
    }
  }

  // Handle general JSON editor errors
  onJsonEditorError(error) {
    this.state.jsonEditorError =
      error.message || "An error occurred in the JSON editor.";
  }

  // Toggle advanced settings visibility
  toggleAdvancedSettings() {
    this.state.showAdvancedSettings = !this.state.showAdvancedSettings;
  }

  onInputChange(fieldName, event) {
    const target = event.target;
    let value;

    // Find the field definition to check its type
    const fieldDef = this.formFields.find((field) => field.name === fieldName);

    if (target.type === "checkbox") {
      value = target.checked;
    } else if (target.type === "number" || target.type === "range") {
      value = parseFloat(target.value);
    } else if (fieldDef && fieldDef.type === "integer") {
      // Convert select dropdown values to integers for integer fields
      value = parseInt(target.value, 10);
    } else {
      value = target.value;
    }

    // Create a new object with the updated value to ensure reactivity
    this.state.formValues = {
      ...this.state.formValues,
      [fieldName]: value,
    };
  }

  _validateFormValues() {
    const errors = [];
    const validatedValues = {}; // This will hold values that conform to the schema
    const currentFormValues = this.state.formValues;
    const schemaFieldNames = new Set(this.formFields.map((f) => f.name)); // For quick lookup

    // Step 1: Check schema-defined fields: required, presence, and type
    for (const schemaField of this.formFields) {
      const fieldName = schemaField.name;
      const label = schemaField.label || fieldName;
      let value = currentFormValues[fieldName];

      if (value === undefined && schemaField.default !== undefined) {
        value = schemaField.default;
      }

      if (schemaField.required) {
        const isMissingOrEmpty =
          value === undefined ||
          value === null ||
          (typeof value === "string" && value.trim() === "") ||
          (Array.isArray(value) && value.length === 0);
        if (isMissingOrEmpty) {
          errors.push(`Field "${label}" is required.`);
          continue;
        }
      }

      if (value !== undefined) {
        let processedValue = value;
        let typeValidationError = null;

        switch (schemaField.type) {
          case "integer":
            const intValue = parseFloat(value);
            if (isNaN(intValue) || !Number.isInteger(intValue)) {
              typeValidationError = `must be an integer. Received: "${value}"`;
            } else {
              processedValue = intValue;
            }
            break;
          case "number":
            const floatValue = parseFloat(value);
            if (isNaN(floatValue)) {
              typeValidationError = `must be a number. Received: "${value}"`;
            } else {
              processedValue = floatValue;
            }
            break;
          case "boolean":
            if (typeof value === "string") {
              if (value.toLowerCase() === "true") processedValue = true;
              else if (value.toLowerCase() === "false") processedValue = false;
              else
                typeValidationError = `expects a boolean (true/false). Received: "${value}"`;
            } else if (typeof value !== "boolean") {
              typeValidationError = `expects a boolean. Received: ${typeof value}`;
            }
            break;
          case "string":
            if (value !== null && value !== undefined) {
              processedValue = String(value);
            }
            break;
          // Add cases for 'enum', 'array', 'object' for more complex schemas if needed
        }

        if (typeValidationError) {
          errors.push(`Field "${label}" ${typeValidationError}.`);
        } else {
          validatedValues[fieldName] = processedValue;
        }
      }
    }

    // Step 2: Check for EXTRA fields
    for (const keyInForm in currentFormValues) {
      if (!schemaFieldNames.has(keyInForm)) {
        console.warn(
          `Extra field "${keyInForm}" provided in form data will be ignored.`
        );
        // Optionally, treat as an error:
        // errors.push(`Field "${keyInForm}" is not a recognized field.`);
      }
    }

    // Step 3: Return validation result
    if (errors.length > 0) {
      return { isValid: false, errors: errors, values: currentFormValues };
    }
    return { isValid: true, errors: [], values: validatedValues };
  }

  /**
   * Format field descriptions to properly display HTML-like content
   * @param {String} description - The raw description text
   * @returns {Markup} - Safely formatted description
   */
  formatDescription(description) {
    if (!description) return "";

    // Format special syntax patterns
    const formattedDesc = description
      // Format code-like elements with monospace font
      .replace(/<([^>]+)>/g, "<code>$1</code>")
      // Format examples with italics
      .replace(/'([^']+)'/g, "<em>$1</em>")
      // Add line breaks for better readability
      .replace(/\. /g, ". <br/>")
      // Format URLs as links
      .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank">$1</a>');

    // Return as safe markup that won't be escaped
    return markup(formattedDesc);
  }
  async onSubmit(event) {
    event.preventDefault();

    // Call the validation function
    const validationResult = this._validateFormValues();

    if (!validationResult.isValid) {
      this.state.error = validationResult.errors.join("\n"); // Display multiple errors
      this.state.isLoading = false;
      return; // Stop submission
    }

    // If validation passes, proceed
    this.state.isLoading = true;
    this.state.error = null; // Clear any previous errors

    if (!this.llmModel) {
      this.state.error = "Model not available.";
      this.state.isLoading = false;
      return;
    }

    try {
      const composer = this.thread.composer;
      // Send only the validated and cleaned values
      composer.postUserMediaGenMessageForLLM(validationResult.values);
    } catch (error) {
      console.error("Error submitting media generation form:", error);
      this.state.error =
        error.message || "An unexpected error occurred during submission.";
    } finally {
      this.state.isLoading = false;
    }
  }
  async onSendJob(event) {
    event.preventDefault();

    // Call the validation function
    const validationResult = this._validateFormValues();

    if (!validationResult.isValid) {
      this.state.error = validationResult.errors.join("\n"); // Display multiple errors
      return; // Stop submission
    }

    // If validation passes, proceed
    this.state.isLoading = true;
    this.state.error = null; // Clear any previous errors

    if (!this.llmModel) {
      this.state.error = "Model not available.";
      this.state.isLoading = false;
      return;
    }

    try {
      // Call backend to create and submit generation job
      const result = await this.env.services.rpc({
        route: '/api/llm/thread/submit_async_generation',
        params: {
          thread_id: this.thread.id,
          generation_inputs: validationResult.values,
          model_id: this.llmModel.id,
        },
      });

      if (result.success) {
        // Show success notification
        this.env.services.notification.add(
          `🚀 Generation job submitted successfully! Job ID: ${result.job_id}`,
          {
            type: 'success',
            sticky: false,
          }
        );
        
        // Clear form error
        this.state.error = null;
      } else {
        this.state.error = result.error || "Failed to submit generation job.";
      }
    } catch (error) {
      console.error("Error submitting generation job:", error);
      
      if (error.message && error.message.includes('404')) {
        this.state.error = "Async generation is not available. The llm_generate_job module may not be installed.";
      } else {
        this.state.error = error.message || "An unexpected error occurred while submitting the job.";
      }
    } finally {
      this.state.isLoading = false;
    }
  }

  isStreaming() {
    return this.thread.composer.isStreaming;
  }
}

LLMMediaForm.props = {
  model: { type: Object, optional: false },
};

LLMMediaForm.template = "llm_thread.LLMMediaForm";

// Register JsonEditorComponent for use in the template
LLMMediaForm.components = { JsonEditorComponent, LLMFormFieldsView };

registerMessagingComponent(LLMMediaForm);
