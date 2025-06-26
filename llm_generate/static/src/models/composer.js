/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";

registerPatch({
  name: "Composer",
  recordMethods: {
    /**
     * Post a user message for media generation with streaming response
     * @param {Object} inputs - Generation inputs according to model schema
     */
    postUserMediaGenMessageForLLM(inputs) {
      const thread = this.thread;

      if (!thread?.id) {
        this.messaging.notify({
          message: this.env._t("Thread not available."),
          type: "danger",
        });
        return;
      }

      const messageBody = inputs.prompt || "Media Generation Request";
      if (!messageBody) {
        this.messaging.notify({
          message: this.env._t("Please enter a message."),
          type: "danger",
        });
        return;
      }

      // Check if the model is configured for media generation
      if (!thread.llmModel?.isMediaGenerationModel) {
        this.messaging.notify({
          message: this.env._t("Selected model is not configured for media generation."),
          type: "danger",
        });
        return;
      }

      this._reset();

      try {
        // Use the existing /llm/thread/generate endpoint with generation_inputs parameter
        const threadId = String(thread.id);
        const encodedMessage = encodeURIComponent(String(messageBody));
        const encodedInputs = encodeURIComponent(JSON.stringify(inputs));

        const url = `/llm/thread/generate?thread_id=${threadId}&message=${encodedMessage}&generation_inputs=${encodedInputs}`;

        console.log("Creating EventSource for media generation:", url);

        const eventSource = new EventSource(url);
        this.update({ eventSource });

        eventSource.onmessage = async (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log("Received media generation event:", data);

            switch (data.type) {
              case "message_create":
                this._handleMessageCreate(data.message);
                break;
              case "message_chunk":
                this._handleMessageUpdate(data.message);
                break;
              case "message_update":
                this._handleMessageUpdate(data.message);
                break;
              case "error":
                this._closeEventSource();
                this.messaging.notify({
                  message: data.error,
                  type: "danger",
                  sticky: true,
                });
                break;
              case "done":
                const sameThread =
                    this.thread?.id === this.thread?.llmChat?.activeThread?.id;
                if (!sameThread) {
                  this.messaging.notify({
                    message:
                        this.env._t("Generation completed for ") +
                        (this.thread.displayName || "thread"),
                    type: "success",
                  });
                }
                this._closeEventSource();
                break;
              default:
                console.warn("Unknown media generation event type:", data.type);
            }
          } catch (parseError) {
            console.error("Error parsing media generation event:", parseError);
            this.messaging.notify({
              message: this.env._t("Error processing server response."),
              type: "danger",
            });
          }
        };

        eventSource.onerror = (error) => {
          console.error("EventSource failed:", error);
          this.messaging.notify({
            message: this.env._t(
                "Connection to server lost. Please try again."
            ),
            type: "danger",
            sticky: true,
          });
          this._closeEventSource();
        };

      } catch (error) {
        console.error("Error initiating media generation:", error);
        this.messaging.notify({
          message: this.env._t("Failed to start media generation: ") + String(error),
          type: "danger",
          sticky: true,
        });
      } finally {
        // Focus composer views
        if (this.composerViews) {
          for (const composerView of this.composerViews) {
            composerView.update({ doFocus: true });
          }
        }
      }
    },
  },
});
