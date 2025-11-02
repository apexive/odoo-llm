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
      if ("user_vote" in data) {
        data2.user_vote = data.user_vote;
      }
      // Add LLM role data from the stored field
      if ("llm_role" in data) {
        data2.llmRole = data.llm_role;
      }
      // Add body_json data for tool messages
      if ("body_json" in data) {
        data2.bodyJson = data.body_json;
      }
      return data2;
    },
    
  },
  fields: {
    // So that assisstant messages with tool_calls but no body does not missed from ui rendering
    isEmpty: {
      compute(){
        return this._super() && !this.bodyJson;
      }
    },
    user_vote: attr({
      default: 0,
    }),

    /**
     * LLM role for this message ('user', 'assistant', 'tool', 'system')
     * This comes directly from the backend stored field
     */
    llmRole: attr({
      default: null,
    }),

    /**
     * JSON body data for tool messages
     */
    bodyJson: attr({
      default: null,
    }),

    /**
     * Get tool data from body_json field for tool/assistant messages
     */
    toolData: attr({
      compute() {
        return ['tool', 'assistant'].includes(this.llmRole) && this.bodyJson ? this.bodyJson : null;
      },
    }),

    /**
     * Get tool call ID from tool data
     */
    toolCallId: attr({
      compute() {
        const toolData = this.toolData;
        return toolData?.tool_call_id || null;
      },
    }),

    /**
     * Get tool call definition from tool data
     */
    toolCallDefinitionFormatted: attr({
      compute() {
        const toolData = this.toolData;
        return toolData?.tool_call || null;
      },
    }),

    /**
     * Get tool call result from tool data
     */
    toolCallResultData: attr({
      compute() {
        const toolData = this.toolData;
        if (toolData) {
          if ("result" in toolData) {
            return toolData.result;
          } else if ("error" in toolData) {
            return { error: toolData.error };
          }
        }
        return null;
      },
    }),

    /**
     * Check if tool call result is an error
     */
    toolCallResultIsError: attr({
      compute() {
        const toolData = this.toolData;
        return toolData && toolData.status === "error";
      },
    }),

    /**
     * Format tool call result for display
     */
    toolCallResultFormatted: attr({
      compute() {
        const resultData = this.toolCallResultData;
        if (resultData === undefined || resultData === null) {
          return "";
        }
        try {
          return typeof resultData === "object"
            ? JSON.stringify(resultData, null, 2)
            : String(resultData);
        } catch (e) {
          console.error("Error formatting tool call result:", e);
          return String(resultData);
        }
      },
    }),

    /**
     * Get tool name from tool data
     */
    toolName: attr({
      compute() {
        const toolData = this.toolData;
        return toolData?.tool_name || null;
      },
    }),

    /**
     * Tool calls associated with bodyJson(normally assistant message may have it)
     */
    toolCalls: attr({
      compute() {
        const toolData = this.toolData;
        return toolData?.tool_calls || [];
      },
    }),
  },
});
