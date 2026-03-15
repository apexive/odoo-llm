/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Deferred } from "@web/core/utils/concurrency";
import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";

/**
 * LLM Store Service - Integrates with existing mail.store
 * Provides LLM-specific functionality without breaking mail components
 *
 * v17 adaptations:
 * - Uses messagingService.isReady instead of mailStore.isReady
 * - Uses mailStore.Message.insert(data, {html:true}) instead of mailStore.insert({"mail.message": [data]})
 * - Uses mailStore.discuss.thread = thread instead of thread.setAsDiscussThread()
 * - Threads loaded via _init_messaging() returning dict with llmThreads key
 */
export const llmStoreService = {
  dependencies: ["orm", "mail.store", "mail.messaging", "notification"],

  start(env, { orm, "mail.store": mailStore, "mail.messaging": messagingService, notification }) {
    // Keep Deferred outside reactive() - reactive proxy breaks Promise behavior
    const _isReady = new Deferred();

    const llmStore = reactive({
      // {id: LLMModel}
      llmModels: {},
      // {id: LLMProvider}
      llmProviders: {},
      // {id: LLMTool}
      llmTools: {},
      // Set<threadId> currently streaming
      streamingThreads: new Set(),
      // Map<threadId, EventSource>
      eventSources: new Map(),
      // Resolves when LLM data is loaded
      isReady: _isReady,
      // Pending AI chat open from client action
      pendingOpenInChatter: null,

      // Computed properties - using mailStore as source of truth
      get activeLLMThread() {
        const activeThread = mailStore.discuss?.thread;
        return activeThread?.model === "llm.thread" ? activeThread : null;
      },

      get isLLMThread() {
        return this.activeLLMThread !== null;
      },

      get llmThreadList() {
        const allThreads = Object.values(mailStore.Thread.records || {});
        return allThreads
          .filter((thread) => thread.model === "llm.thread")
          .sort(
            (a, b) => new Date(b.write_date || 0) - new Date(a.write_date || 0)
          );
      },

      async ensureThreadLoaded(threadId) {
        const thread = mailStore.Thread.get({
          model: "llm.thread",
          id: threadId,
        });
        if (thread) {
          return thread;
        }

        console.warn(`Thread ${threadId} not found in mailStore`);
        return null;
      },

      async sendLLMMessage(threadId, content, attachmentIds = []) {
        if (!threadId || (!content?.trim() && attachmentIds.length === 0)) {
          return;
        }

        try {
          await this.startLLMStreaming(threadId, content, attachmentIds);
        } catch (error) {
          console.error("Error sending LLM message:", error);
          notification.add(
            _t(
              "Could not send your message. Please check your connection and try again."
            ),
            { type: "danger" }
          );
        }
      },

      async startLLMStreaming(threadId, message, attachmentIds = []) {
        this.stopStreaming(threadId);

        this.streamingThreads.add(threadId);

        try {
          let url = `/llm/thread/generate?thread_id=${threadId}`;
          if (message) {
            url += `&message=${encodeURIComponent(message)}`;
          }
          if (attachmentIds.length > 0) {
            url += `&attachment_ids=${attachmentIds.join(",")}`;
          }
          const eventSource = new EventSource(url);

          this.eventSources.set(threadId, eventSource);

          eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleStreamMessage(threadId, data);
          };

          eventSource.onerror = (error) => {
            console.error("EventSource error:", error);
            this.stopStreaming(threadId);
            notification.add(
              _t(
                "Lost connection to AI service. Please try sending your message again."
              ),
              {
                type: "danger",
              }
            );
          };
        } catch (error) {
          console.error("Error starting stream:", error);
          this.stopStreaming(threadId);
          notification.add(
            _t(
              "Could not start AI response. Please check your connection and try again."
            ),
            { type: "danger" }
          );
        }
      },

      stopStreaming(threadId) {
        const eventSource = this.eventSources.get(threadId);
        if (eventSource) {
          eventSource.close();
          this.eventSources.delete(threadId);
        }
        this.streamingThreads.delete(threadId);
      },

      handleStreamMessage(threadId, data) {
        // Get the thread - try both Thread.get and discuss.thread
        const _getThread = () => {
          return mailStore.Thread.get({
            model: "llm.thread",
            id: threadId,
          }) || (mailStore.discuss?.thread?.model === "llm.thread" && mailStore.discuss.thread.id === threadId ? mailStore.discuss.thread : null);
        };

        switch (data.type) {
          case "message_create": {
            // v17: Use mailStore.Message.insert()
            const createdMessage = mailStore.Message.insert(data.message, { html: true });

            const createThread = _getThread();
            if (
              createThread &&
              createdMessage &&
              !createThread.messages.some((m) => m.id === createdMessage.id)
            ) {
              createThread.messages.push(createdMessage);
            } else {
              console.warn("[LLM] Could not push message to thread", {
                threadFound: !!createThread,
                messageCreated: !!createdMessage,
                threadId,
              });
            }
            break;
          }

          case "message_chunk":
          case "message_update": {
            // v17: Update message data
            mailStore.Message.insert(data.message, { html: true });
            break;
          }

          case "error":
            console.error("Stream error:", data.error);
            this.stopStreaming(threadId);
            notification.add(data.error || _t("AI response error"), {
              type: "danger",
            });
            break;

          case "done":
            this.stopStreaming(threadId);
            break;

          case "tool_called":
          case "tool_succeeded":
          case "tool_failed":
            console.log("[LLM] no-op event:", data.type);
            break;

          default:
            console.warn("Unknown stream message type:", data.type);
            break;
        }
      },

      async loadLLMModels() {
        try {
          const models = await orm.searchRead(
            "llm.model",
            [["active", "=", true]],
            ["id", "name", "provider_id", "default", "model_use"]
          );

          models.forEach((model) => {
            this.llmModels[model.id] = model;
          });
        } catch (error) {
          console.warn(
            "LLM models not available - llm module may not be installed:",
            error.message
          );
        }
      },

      async loadLLMProviders() {
        try {
          const providers = await orm.searchRead(
            "llm.provider",
            [["active", "=", true]],
            ["id", "name", "service"]
          );

          providers.forEach((provider) => {
            this.llmProviders[provider.id] = provider;
          });
        } catch (error) {
          console.warn(
            "LLM providers not available - llm module may not be installed:",
            error.message
          );
        }
      },

      async loadLLMTools() {
        const tools = await orm.searchRead(
          "llm.tool",
          [["active", "=", true]],
          ["id", "name"]
        );

        tools.forEach((tool) => {
          this.llmTools[tool.id] = tool;
        });
      },

      // Thread selection using standard Odoo v17 patterns
      async selectThread(threadId) {
        await _isReady;
        try {
          const thread = await this.ensureThreadLoaded(threadId);
          if (!thread) {
            throw new Error("Thread not found or failed to load");
          }

          // v17: Set thread directly on discuss instead of thread.setAsDiscussThread()
          mailStore.discuss.thread = thread;
        } catch (error) {
          console.error("Error selecting thread:", error);
          notification.add(
            _t(
              "Could not load this conversation. It may have been deleted or you may not have access."
            ),
            { type: "danger" }
          );
        }
      },

      async createNewThread({ recordModel, recordId } = {}) {
        // Ensure LLM data is loaded before checking providers/models
        await _isReady;

        const firstProvider = this.getFirstAvailableProvider();
        const firstModel = this.getFirstAvailableModel();

        if (!firstProvider) {
          notification.add(
            _t(
              "No AI providers are configured. Please contact your administrator to set up an AI provider."
            ),
            { type: "danger" }
          );
          return;
        }

        if (!firstModel) {
          notification.add(
            _t(
              "No AI models are available. Please contact your administrator to configure AI models."
            ),
            { type: "danger" }
          );
          return;
        }

        const threadName = `Chat ${new Date().toLocaleString()}`;

        const threadData = {
          name: threadName,
          provider_id: firstProvider.id,
          model_id: firstModel.id,
        };

        if (recordModel && recordId) {
          threadData.model = recordModel;
          threadData.res_id = recordId;
        }

        const threadId = await orm.call("llm.thread", "create", [threadData]);

        await this.refreshThreadsAndSelect(threadId);
      },

      getFirstAvailableProvider() {
        const providers = Object.values(this.llmProviders);
        return providers.length > 0 ? providers[0] : null;
      },

      getFirstAvailableModel() {
        const models = Object.values(this.llmModels);
        return models.length > 0 ? models[0] : null;
      },

      async refreshThreadsAndSelect(threadId) {
        // v17: Read thread data directly (can't call _init_messaging remotely)
        try {
          const threadData = await orm.read("llm.thread", [threadId], [
            "name", "provider_id", "model_id", "write_date",
          ]);
          if (threadData.length > 0) {
            mailStore.Thread.insert({
              id: threadId,
              model: "llm.thread",
              name: threadData[0].name,
              provider_id: threadData[0].provider_id,
              model_id: threadData[0].model_id,
              write_date: threadData[0].write_date,
              channel_type: "llm_chat",
              isLoaded: true,
            });
          }
        } catch (error) {
          console.warn("Could not refresh threads:", error);
        }

        await this.selectThread(threadId);
      },

      async linkRecordToThread(threadId, model, recordId) {
        try {
          await orm.write("llm.thread", [threadId], {
            model: model,
            res_id: recordId,
          });

          const thread = mailStore.Thread.get({
            model: "llm.thread",
            id: threadId,
          });

          if (thread) {
            Object.assign(thread, {
              res_model: model,
              res_id: recordId,
            });
          }

          notification.add(_t("Record linked to conversation successfully."), {
            type: "success",
          });
          return true;
        } catch (error) {
          console.error("Error linking record:", error);
          notification.add(
            _t(
              "Could not link the record to this conversation. Please try again."
            ),
            { type: "danger" }
          );
          return false;
        }
      },

      async unlinkRecordFromThread(threadId) {
        try {
          await orm.write("llm.thread", [threadId], {
            model: false,
            res_id: false,
          });

          const thread = mailStore.Thread.get({
            model: "llm.thread",
            id: threadId,
          });

          if (thread) {
            Object.assign(thread, {
              res_model: false,
              res_id: false,
            });
          }

          notification.add(
            _t("Record unlinked from conversation successfully."),
            {
              type: "success",
            }
          );
          return true;
        } catch (error) {
          console.error("Error unlinking record:", error);
          notification.add(
            _t(
              "Could not unlink the record from this conversation. Please try again."
            ),
            { type: "danger" }
          );
          return false;
        }
      },

      isStreamingThread(threadId) {
        return this.streamingThreads.has(threadId);
      },

      getStreamingStatus() {
        const activeThread = mailStore.discuss?.thread;
        if (activeThread?.model === "llm.thread") {
          return this.isStreamingThread(activeThread.id);
        }
        return false;
      },

      setPendingOpenInChatter(data) {
        this.pendingOpenInChatter = data;
      },

      consumePendingOpenInChatter(model, resId) {
        const pending = this.pendingOpenInChatter;
        if (pending && pending.model === model && pending.resId === resId) {
          this.pendingOpenInChatter = null;
          return pending;
        }
        return null;
      },

      getDataLoaders() {
        return [this.loadLLMProviders, this.loadLLMModels, this.loadLLMTools];
      },

      async initialize() {
        try {
          const loaders = this.getDataLoaders();
          await Promise.all(loaders.map((loader) => loader.call(this)));
          _isReady.resolve();
        } catch (error) {
          console.error("Error initializing LLM store:", error);
          _isReady.reject(error);
        }
      },

      destroy() {
        this.eventSources.forEach((eventSource) => eventSource.close());
        this.eventSources.clear();
        this.streamingThreads.clear();
      },
    });

    // v17: Use messagingService.isReady instead of mailStore.isReady
    messagingService.isReady.then((data) => {
      // Insert LLM threads from init_messaging response
      if (data?.llmThreads) {
        data.llmThreads.forEach((threadInfo) => {
          mailStore.Thread.insert({ ...threadInfo, isLoaded: true });
        });
      }
      llmStore.initialize();
    });

    return llmStore;
  },
};

registry.category("services").add("llm.store", llmStoreService);
