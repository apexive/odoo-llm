/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";

/**
 * LLM Store Service - Integrates with existing mail.store
 * Provides LLM-specific functionality without breaking mail components
 */
export const llmStoreService = {
  dependencies: ["orm", "mail.store", "mail.thread", "notification", "mail.messaging"],

  start(env, { orm, "mail.store": mailStore, "mail.thread": threadService, notification, "mail.messaging": messaging }) {
    const llmStore = reactive({
      // NOTE: Threads are now loaded via standard mail.store, no need for separate Map
      llmModels: new Map(), // Map<id, LLMModel>
      llmProviders: new Map(), // Map<id, LLMProvider>
      llmTools: new Map(), // Map<id, LLMTool>
      streamingThreads: new Set(), // Set<threadId> currently streaming
      eventSources: new Map(), // Map<threadId, EventSource>
      isReady: new Deferred(), // Resolves when LLM data is loaded

      // Computed properties - using mailStore as source of truth
      get activeLLMThread() {
        // Check if current active thread in mail.store is an LLM thread
        const activeThread = mailStore.discuss?.thread;
        return activeThread?.model === "llm.thread" ? activeThread : null;
      },

      get isLLMThread() {
        return this.activeLLMThread !== null;
      },

      get llmThreadList() {
        // Get all LLM threads from mailStore
        // Add defensive checks for mailStore.Thread and records
        if (!mailStore.Thread || !mailStore.Thread.records) {
          console.warn("mailStore.Thread.records is not available yet");
          return [];
        }
        const allThreads = Object.values(mailStore.Thread.records);
        return allThreads
          .filter((thread) => thread.model === "llm.thread")
          .sort(
            (a, b) => new Date(b.write_date || 0) - new Date(a.write_date || 0)
          );
      },

      // LLM-specific methods using standard fetchData approach
      async ensureThreadLoaded(threadId) {
        // Check if mailStore.Thread is available
        if (!mailStore.Thread) {
          console.error("mailStore.Thread is not available");
          return null;
        }

        // Check if thread already exists in mailStore
        const thread = mailStore.Thread.get({
          model: "llm.thread",
          id: threadId,
        });
        if (thread) {
          return thread;
        }

        // If thread not found, it might not be accessible to current user
        // or wasn't loaded in init_messaging (e.g., old thread, different user)
        console.warn(`Thread ${threadId} not found in mailStore`);
        return null;
      },

      async sendLLMMessage(threadId, content) {
        if (!threadId || !content?.trim()) return;

        try {
          // Start LLM streaming - backend will handle both user message creation and AI response
          await this.startLLMStreaming(threadId, content);
        } catch (error) {
          console.error("Error sending LLM message:", error);
          notification.add("Failed to send message", { type: "danger" });
        }
      },

      async startLLMStreaming(threadId, message) {
        // Stop any existing stream for this thread
        this.stopStreaming(threadId);

        this.streamingThreads.add(threadId);

        try {
          // Include message parameter for user message creation
          const eventSource = new EventSource(
            `/llm/thread/generate?thread_id=${threadId}&message=${encodeURIComponent(
              message
            )}`
          );

          this.eventSources.set(threadId, eventSource);

          eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleStreamMessage(threadId, data);
          };

          eventSource.onerror = (error) => {
            console.error("EventSource error:", error);
            this.stopStreaming(threadId);
            notification.add("Connection error during AI response", {
              type: "danger",
            });
          };
        } catch (error) {
          console.error("Error starting stream:", error);
          this.stopStreaming(threadId);
          notification.add("Failed to start AI response", { type: "danger" });
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
        switch (data.type) {
          case "message_create":
            // Handle all messages (user and AI) via EventSource
            mailStore.insert(
              { "mail.message": [data.message] },
              { html: true }
            );

            // Get the created message and add it to the thread's messages collection
            const createdMessage = mailStore.Message.get(data.message.id);

            // Add message to the thread's messages collection if not already there
            const createThread = mailStore.discuss?.thread;
            if (
              createThread &&
              createdMessage &&
              !createThread.messages.some((m) => m.id === createdMessage.id)
            ) {
              createThread.messages.push(createdMessage);
            }
            break;

          case "message_chunk":
          case "message_update":
            // Update existing message using standard mail.store.insert() like Odoo does
            // Use the same pattern as Odoo's standard bus handlers - always use insert
            // which will update existing messages or create new ones as needed
            mailStore.insert(
              { "mail.message": [data.message] },
              { html: true }
            );
            break;

          case "error":
            console.error("Stream error:", data.error);
            this.stopStreaming(threadId);
            notification.add(data.error || "AI response error", {
              type: "danger",
            });
            break;

          case "done":
            this.stopStreaming(threadId);
            break;

          default:
            console.warn("Unknown stream message type:", data.type);
            break;
        }
      },

      async loadLLMModels() {
        try {
          // Check if llm.model exists first - use correct field names
          const models = await orm.searchRead(
            "llm.model",
            [["active", "=", true]],
            ["id", "name", "provider_id", "default", "model_use"]
          );

          models.forEach((model) => {
            this.llmModels.set(model.id, model);
          });
        } catch (error) {
          console.warn(
            "LLM models not available - llm module may not be installed:",
            error.message
          );
          // Don't throw error, just log warning
        }
      },

      async loadLLMProviders() {
        try {
          // Check if llm.provider exists first - use correct field names
          const providers = await orm.searchRead(
            "llm.provider",
            [["active", "=", true]],
            ["id", "name", "service"]
          );

          providers.forEach((provider) => {
            this.llmProviders.set(provider.id, provider);
          });
        } catch (error) {
          console.warn(
            "LLM providers not available - llm module may not be installed:",
            error.message
          );
          // Don't throw error, just log warning
        }
      },

      async loadLLMTools() {
        // Load available tools with minimal fields
        const tools = await orm.searchRead(
          "llm.tool",
          [["active", "=", true]],
          ["id", "name"]
        );

        tools.forEach((tool) => {
          this.llmTools.set(tool.id, tool);
        });
      },

      // Thread selection using standard Odoo 17 patterns
      async selectThread(threadId) {
        try {
          // Ensure thread is loaded using standard fetchData
          const thread = await this.ensureThreadLoaded(threadId);
          if (!thread) {
            throw new Error(`Thread ${threadId} not found or failed to load`);
          }

          // Use Odoo 17's threadService.setDiscussThread() method
          threadService.setDiscussThread(thread);
        } catch (error) {
          console.error("Error selecting thread:", error);
          // Log detailed error information
          console.error("Error details:", {
            threadId: threadId,
            message: error.message,
            stack: error.stack,
            error: error,
          });
          notification.add(
            `Failed to load chat thread: ${error.message || "Unknown error"}`,
            {
              type: "danger",
              sticky: true, // Make notification persistent
            }
          );
          throw error; // Re-throw so caller can handle
        }
      },

      // Create new thread with default provider and model
      async createNewThread() {
        // Get first available provider and model
        const firstProvider = this.getFirstAvailableProvider();
        const firstModel = this.getFirstAvailableModel();

        // Check for null values and show notifications
        if (!firstProvider) {
          notification.add(
            "No LLM providers available. Please configure at least one provider.",
            { type: "danger" }
          );
          return;
        }

        if (!firstModel) {
          notification.add(
            "No LLM models available. Please configure at least one model.",
            { type: "danger" }
          );
          return;
        }

        // Create thread with auto-generated name
        const threadName = `Chat ${new Date().toLocaleString()}`;

        const threadId = await orm.call("llm.thread", "create", [
          {
            name: threadName,
            provider_id: firstProvider.id,
            model_id: firstModel.id,
          },
        ]);

        // Reload user threads and select the new one
        await this.refreshThreadsAndSelect(threadId);
      },

      // Get first available provider
      getFirstAvailableProvider() {
        const providers = Array.from(this.llmProviders.values());
        return providers.length > 0 ? providers[0] : null;
      },

      // Get first available model
      getFirstAvailableModel() {
        const models = Array.from(this.llmModels.values());
        return models.length > 0 ? models[0] : null;
      },

      // Refresh threads and select specific thread
      async refreshThreadsAndSelect(threadId) {
        // Use proper fetchData to refresh thread data
        await mailStore.fetchData({
          init_messaging: {}, // Will trigger proper reload of all threads
        });

        // Wait a moment for threads to be populated
        await new Promise((resolve) => setTimeout(resolve, 100));

        // Select the newly created thread
        await this.selectThread(threadId);
      },

      // Helper methods for components
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

      // Get list of data loaders - can be extended by patches
      getDataLoaders() {
        return [this.loadLLMProviders, this.loadLLMModels, this.loadLLMTools];
      },

      // Initialize LLM store - threads now loaded via standard init_messaging
      async initialize() {
        try {
          const loaders = this.getDataLoaders();
          await Promise.all(loaders.map((loader) => loader.call(this)));
          // NOTE: LLM threads are now loaded automatically via res.users._init_messaging()
          this.isReady.resolve();
        } catch (error) {
          console.error("Error initializing LLM store:", error);
          // Log detailed error information
          console.error("LLM store initialization error details:", {
            message: error.message,
            stack: error.stack,
            error: error,
          });
          notification.add(
            `Failed to initialize LLM store: ${error.message || "Unknown error"}`,
            {
              type: "danger",
              sticky: true,
            }
          );
          this.isReady.reject(error);
        }
      },

      // Cleanup
      destroy() {
        // Close all event sources
        this.eventSources.forEach((eventSource) => eventSource.close());
        this.eventSources.clear();
        this.streamingThreads.clear();
      },
    });

    // Initialize LLM data after messaging is ready (which calls init_messaging)
    // The messaging service has the isReady promise, not mail.store
    messaging.isReady.then(() => {
      llmStore.initialize();
    });

    // NOTE: No longer need thread subscription since threads load automatically via fetchData

    return llmStore;
  },
};

registry.category("services").add("llm.store", llmStoreService);
