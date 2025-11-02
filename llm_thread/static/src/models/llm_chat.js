/** @odoo-module **/

import { attr, many, one } from "@mail/model/model_field";
import { clear } from "@mail/model/model_field_command";
import { registerModel } from "@mail/model/model_core";

// Constants for thread fields
const THREAD_SEARCH_FIELDS = [
  "name",
  "message_ids",
  "create_uid",
  "create_date",
  "write_date",
  "model_id",
  "provider_id",
  "model",
  "res_id",
  "tool_ids",
  "prompt_id",
];

registerModel({
  name: "LLMChat",
  recordMethods: {
    /**
     * Closes the LLM chat and resets its view state.
     */
    close() {
      this.update({ llmChatView: clear() });
    },

    /**
     * Opens the initial thread based on initActiveId or defaults to the first thread.
     */
    openInitThread() {
      if (!this.initActiveId) {
        if (this.threads.length > 0) {
          this.selectThread(this.threads[0].id);
        }
        return;
      }

      const [model, id] =
        typeof this.initActiveId === "number"
          ? ["llm.thread", this.initActiveId]
          : this.initActiveId.split("_");
      const thread = this.messaging.models.Thread.findFromIdentifyingData({
        id: Number(id),
        model,
      });
      if (!thread && this.threads.length > 0) {
        this.selectThread(this.threads[0].id);
      } else if (thread) {
        this.selectThread(thread.id);
      }
    },

    /**
     * Opens a specific thread in the LLM chat UI.
     * @param {Thread} thread
     */
    async openThread(thread) {
      this.update({ thread });
      if (!this.llmChatView) {
        this.env.services.action.doAction("llm_thread.action_llm_chat", {
          name: this.env._t("Chat"),
          active_id: this.threadToActiveId(thread),
          clearBreadcrumbs: false,
        });
      }
    },

    /**
     * Formats a thread into an active ID string.
     * @param {Thread} thread
     * @returns {String}
     */
    threadToActiveId(thread) {
      return `${thread.model}_${thread.id}`;
    },

    /**
     * Load threads from the server for the current user.
     * @param {Array} [additionalFields=[]] - Additional fields to fetch
     */
    async loadThreads(additionalFields = []) {
      const result = await this.messaging.rpc({
        model: "llm.thread",
        method: "search_read",
        kwargs: {
          domain: [["create_uid", "=", this.env.services.user.userId]],
          fields: [...THREAD_SEARCH_FIELDS, ...additionalFields],
          order: "write_date desc",
        },
      });

      const threadData = result.map((thread) =>
        this._mapThreadDataFromServer(thread)
      );
      this.update({ threads: threadData });
    },

    /**
     * Maps server thread data to the format expected by the Thread model
     * @param {Object} threadData - Raw thread data from server
     * @returns {Object} - Formatted thread data
     * @private
     */
    _mapThreadDataFromServer(threadData) {
      const mappedData = {
        id: threadData.id,
        model: "llm.thread",
        name: threadData.name,
        message_needaction_counter: 0,
        creator: threadData.create_uid
          ? { id: threadData.create_uid }
          : undefined,
        isServerPinned: true,
        updatedAt: threadData.write_date,
        relatedThreadModel: threadData.model,
        relatedThreadId: threadData.res_id,
        selectedToolIds: threadData.tool_ids || [],
        promptId: threadData.prompt_id || null,
      };

      // Handle the llmModel field separately to avoid undefined errors
      if (threadData.model_id && threadData.provider_id) {
        mappedData.llmModel = {
          id: threadData.model_id[0],
          name: threadData.model_id[1],
          llmProvider: {
            id: threadData.provider_id[0],
            name: threadData.provider_id[1],
          },
        };
      }

      return mappedData;
    },

    /**
     * Refreshes a specific thread in the threads collection.
     * @param {Number} threadId - ID of the thread to refresh
     * @param {Array} [additionalFields=[]] - Additional fields to fetch
     * @returns {Promise<void>}
     */
    async refreshThread(threadId, additionalFields = []) {
      try {
        const result = await this.messaging.rpc({
          model: "llm.thread",
          method: "search_read",
          kwargs: {
            domain: [["id", "=", threadId]],
            fields: [...THREAD_SEARCH_FIELDS, ...additionalFields],
          },
        });

        if (!result || !result.length) {
          return;
        }

        const mappedThreadData = this._mapThreadDataFromServer(result[0]);

        // Find the thread in the collection and update it directly
        if (this.threads) {
          const threadIndex = this.threads.findIndex(
            (thread) => thread.id === threadId
          );

          if (threadIndex !== -1) {
            // Get the existing thread
            const thread = this.threads[threadIndex];

            // Update the thread directly
            thread.update(mappedThreadData);
          }
        }
      } catch (error) {
        console.error("Error refreshing thread:", error);
      }
    },

    /**
     * Selects a thread by ID as the active thread.
     * @param {Number} threadId
     */
    async selectThread(threadId) {
      const thread = this.messaging.models.Thread.findFromIdentifyingData({
        id: threadId,
        model: "llm.thread",
      });
      if (thread) {
        this.update({ activeThread: thread });
      }
    },

    /**
     * Opens the LLM chat view.
     */
    open() {
      this.update({ llmChatView: {} });
    },

    /**
     * Loads LLM models from the server.
     */
    async loadLLMModels() {
      const result = await this.messaging.rpc({
        model: "llm.model",
        method: "search_read",
        kwargs: {
          domain: [],
          fields: ["name", "id", "provider_id", "default"],
        },
      });

      const llmModelData = result.map((model) => ({
        id: model.id,
        name: model.name,
        llmProvider: model.provider_id
          ? { id: model.provider_id[0], name: model.provider_id[1] }
          : undefined,
        default: model.default,
      }));

      this.update({ llmModels: llmModelData });
    },

    /**
     * Creates a new thread with optional related thread info.
     * @param {Object} params - Thread creation parameters
     * @param {String} params.name - Thread name
     * @param {String} [params.relatedThreadModel] - Related thread model
     * @param {Number} [params.relatedThreadId] - Related thread ID
     * @returns {Promise<Object|null>} The created thread or null if failed
     * @throws {Error} If no LLM model is available
     */
    async createThread({ name, relatedThreadModel, relatedThreadId }) {
      const defaultModel = this.defaultLLMModel;
      if (!defaultModel) {
        this.messaging.notify({
          title: "No LLMModel available",
          message: "Please add a new LLMModel to use this feature",
          type: "warning",
        });
        // Throw an error instead of returning null to make the failure more explicit
        throw new Error("No LLM model available");
      }

      const threadData = {
        name,
        model_id: defaultModel.id,
        provider_id: defaultModel.llmProvider.id,
      };
      if (relatedThreadModel && relatedThreadId) {
        threadData.model = relatedThreadModel;
        threadData.res_id = relatedThreadId;
      }

      const threadId = await this.messaging.rpc({
        model: "llm.thread",
        method: "create",
        args: [[threadData]],
      });

      const threadDetails = await this.messaging.rpc({
        model: "llm.thread",
        method: "read",
        args: [[threadId], ["name", "model_id", "provider_id", "write_date"]],
      });

      if (!threadDetails || !threadDetails[0]) {
        this.messaging.notify({
          title: "Error",
          message: "Failed to create thread",
          type: "danger",
        });
        return null;
      }

      const thread = this.messaging.models.Thread.insert({
        id: threadId,
        model: "llm.thread",
        name: threadDetails[0].name,
        message_needaction_counter: 0,
        isServerPinned: true,
        llmModel: defaultModel,
        llmChat: this,
        updatedAt: threadDetails[0].write_date,
        ...(relatedThreadModel && { relatedThreadModel }),
        ...(relatedThreadId && { relatedThreadId }),
      });

      return thread;
    },

    /**
     * Ensures LLM models and threads are loaded, creating a thread if needed.
     * @param {Object} [options] - Optional parameters
     * @param {String} [options.relatedThreadModel] - Related thread model
     * @param {Number} [options.relatedThreadId] - Related thread ID
     * @returns {Promise<Object|null>} The active or created thread
     */
    async ensureThread({ relatedThreadModel, relatedThreadId } = {}) {
      if (this.llmModels.length === 0) {
        await this.loadLLMModels();
      }
      if (this.threads.length === 0) {
        await this.loadThreads();
      }
      // Load tools if not already loaded
      if (!this.tools || this.tools.length === 0) {
        await this.loadTools();
      }

      if (relatedThreadModel && relatedThreadId) {
        const existingThread = this.threads.find(
          (thread) =>
            thread.relatedThreadModel === relatedThreadModel &&
            thread.relatedThreadId === relatedThreadId
        );
        if (existingThread) {
          return existingThread;
        }

        try {
          const name = `AI Chat for ${relatedThreadModel} ${relatedThreadId}`;
          return await this.createThread({
            name,
            relatedThreadModel,
            relatedThreadId,
          });
        } catch (error) {
          console.error("Failed to create thread for related model:", error);
          // Fall through to use existing threads or create a generic thread
        }
      }

      if (this.threads.length > 0) {
        return this.threads[0];
      }

      try {
        const name = `New Chat ${new Date().toLocaleString()}`;
        return await this.createThread({ name });
      } catch (error) {
        console.error("Failed to create default thread:", error);
        return null;
      }
    },

    async createNewThread() {
      try {
        const name = `New Chat ${new Date().toLocaleString()}`;
        const thread = await this.createThread({ name });
        if (thread) {
          this.selectThread(thread.id);
        }
      } catch (error) {
        console.error("Failed to create new thread:", error);
        // Error notification is already shown in createThread
      }
    },

    /**
     * Initialize the LLM chat with the given action.
     * @param {Object} action - The action that triggered the initialization
     * @param {Number} initActiveId - The ID of the thread to initialize with
     * @param {Array} [postInitializationPromises=[]] - Additional promises to execute after loading basic resources
     */
    async initializeLLMChat(
      action,
      initActiveId,
      postInitializationPromises = []
    ) {
      this.update({
        llmChatView: {
          actionId: action.id,
        },
        initActiveId,
      });

      // Wait for messaging to be initialized
      await this.messaging.initializedPromise;
      await this.loadLLMModels();
      // Load threads first
      await this.loadThreads();
      await this.loadTools();

      // Execute any additional initialization promises
      if (postInitializationPromises.length > 0) {
        await Promise.all(postInitializationPromises);
      }

      // Then handle initial thread
      if (!this.isInitThreadHandled) {
        this.update({ isInitThreadHandled: true });
        if (!this.activeThread) {
          this.openInitThread();
        }
      }
    },

    /**
     * Load tools from the server
     */
    async loadTools() {
      try {
        const result = await this.messaging.rpc({
          model: "llm.tool",
          method: "search_read",
          kwargs: {
            domain: [["active", "=", true]],
            fields: ["name", "id"],
          },
        });

        const toolData = result.map((tool) => ({
          id: tool.id,
          name: tool.name,
        }));

        this.update({ tools: toolData });
      } catch (error) {
        console.error("Error loading tools:", error);
        return [];
      }
    },
  },
  fields: {
    activeId: attr({
      compute() {
        return this.activeThread
          ? this.threadToActiveId(this.activeThread)
          : clear();
      },
    }),
    llmChatView: one("LLMChatView", { inverse: "llmChat", isCausal: true }),
    isInitThreadHandled: attr({ default: false }),
    initActiveId: attr({ default: null }),
    activeThread: one("Thread", { inverse: "activeLLMChat" }),
    threads: many("Thread", { inverse: "llmChat" }),
    orderedThreads: many("Thread", {
      compute() {
        if (!this.threads) return clear();
        return this.threads.slice().sort((a, b) => {
          const dateA = a.updatedAt
            ? new Date(a.updatedAt.replace(" ", "T"))
            : new Date(0);
          const dateB = b.updatedAt
            ? new Date(b.updatedAt.replace(" ", "T"))
            : new Date(0);
          return dateB - dateA;
        });
      },
    }),
    threadCache: one("ThreadCache", {
      compute() {
        return this.activeThread ? { thread: this.activeThread } : clear();
      },
    }),
    llmModels: many("LLMModel"),
    llmProviders: many("LLMProvider", {
      compute() {
        if (!this.llmModels || !Array.isArray(this.llmModels)) {
          return [];
        }
        const providers = this.llmModels
          .map((m) => (m && m.llmProvider ? m.llmProvider : null))
          .filter((p) => p && p.id);
        return [...new Map(providers.map((p) => [p.id, p])).values()];
      },
    }),
    defaultLLMModel: one("LLMModel", {
      compute() {
        if (!this.llmModels || !Array.isArray(this.llmModels)) {
          return clear();
        }
        const activeModel = this.activeThread?.llmModel;
        if (!activeModel) {
          return this.llmModels.length > 0 && this.llmModels[0]
            ? this.llmModels[0]
            : clear();
        }

        const found = this.llmModels.find((m) => m && m.id === activeModel.id);
        return found ? found : clear();
      },
    }),
    tools: many("LLMTool"),
  },
});
