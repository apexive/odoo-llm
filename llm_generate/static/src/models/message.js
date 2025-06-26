/** @odoo-module **/

import { attr } from "@mail/model/model_field";
import { registerPatch } from "@mail/model/model_core";

/**
 * Helper function to safely parse JSON strings.
 * Returns defaultValue if parsing fails or input is invalid.
 * @param {String} jsonString - JSON string to parse
 * @param {any} [defaultValue=undefined] - Default value on failure
 * @returns {any} Parsed JSON or defaultValue
 */
function safeJsonParse(jsonString, defaultValue = undefined) {
  if (!jsonString || typeof jsonString !== "string") {
    return defaultValue;
  }
  try {
    return JSON.parse(jsonString);
  } catch (e) {
    console.warn("Failed to parse JSON string:", jsonString, e);
    return defaultValue;
  }
}

registerPatch({
  name: "Message",
  modelMethods: {
    /**
     * @override
     */
    convertData(data) {
      const data2 = this._super(data);
      if ("generation_inputs" in data) {
        data2.generationInputs = data.generation_inputs;
      }
      return data2;
    },
  },
  fields: {
    generationInputs: attr({
      default: null,
    }),

    generationInputsFormatted: attr({
      compute() {
        const jsonVal = safeJsonParse(this.generationInputs);
        if (jsonVal === undefined || jsonVal === null) {
          return "{}";
        }

        try {
          // Only pretty print if it's likely an object/array
          return typeof jsonVal === "object"
              ? JSON.stringify(jsonVal, null, 2)
              : String(jsonVal);
        } catch (e) {
          console.error("Error formatting generation inputs:", e);
          return String(jsonVal);
        }
      },
    }),

    /**
     * Check if this message is a user media generation message
     */
    isLLMUserMediaGenMessage: attr({
      compute() {
        return (
            this.messageSubtypeXmlid === 'llm_mail_message_subtypes.mt_llm_user' &&
            Boolean(this.generationInputs)
        );
      },
    }),

    /**
     * Get parsed generation inputs as object
     */
    generationInputsParsed: attr({
      compute() {
        return safeJsonParse(this.generationInputs, {});
      },
    }),
  },
});
