/** @odoo-module **/

import { Messaging } from "@mail/core/common/messaging_service";
import { patch } from "@web/core/utils/patch";

/**
 * Patch Messaging service to handle llm_threads data from init_messaging
 */
patch(Messaging.prototype, {
  /**
   * Override initMessagingCallback to process llm_threads data
   */
  initMessagingCallback(data) {
    // Call parent implementation first
    super.initMessagingCallback(data);

    // Process llm_threads if present in the response
    if (data.llm_threads && Array.isArray(data.llm_threads)) {
      // Insert LLM threads into the mail store using the standard Thread.insert pattern
      // Each thread should have model: "llm.thread"
      data.llm_threads.forEach((threadData) => {
        try {
          this.store.Thread.insert({
            ...threadData,
            model: "llm.thread",
            // Ensure required fields are present
            id: threadData.id,
            type: threadData.type || "llm_thread",
          });
        } catch (error) {
          console.error(
            `Error inserting LLM thread ${threadData.id}:`,
            error
          );
        }
      });

      console.log(
        `Loaded ${data.llm_threads.length} LLM threads into mail store`
      );
    }
  },
});
