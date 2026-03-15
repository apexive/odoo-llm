/** @odoo-module **/

// v17: Chatter import path is different from v18
import { Chatter } from "@mail/core/web/chatter";
import { LLMChatContainer } from "@llm_thread/components/llm_chat_container/llm_chat_container";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onMounted, useEffect } from "@odoo/owl";

// Register LLMChatContainer component with Chatter
Object.assign(Chatter.components, { LLMChatContainer });

/**
 * Patch Chatter to add AI Chat functionality
 *
 * v17 adaptations:
 * - Import from @mail/core/web/chatter
 * - Use store.discuss.thread = thread instead of thread.setAsDiscussThread()
 * - Use threadService.fetchData() instead of thread.fetchData()
 */
patch(Chatter.prototype, {
  setup() {
    super.setup();
    this.orm = useService("orm");
    this.notification = useService("notification");
    this.threadService = useService("mail.thread");

    // Add LLM chat state
    Object.assign(this.state, {
      isChattingWithLLM: false,
      llmThreadId: null,
    });

    // React to AI chat state changes
    useEffect(
      () => {
        if (this.state.isChattingWithLLM) {
          this.focusComposerWhenReady();
        }
      },
      () => [this.state.isChattingWithLLM]
    );

    // Check for pending AI chat open from client action
    onMounted(() => {
      this.checkPendingAIChatOpen();
    });
  },

  async checkPendingAIChatOpen() {
    const llmStore = this.env.services["llm.store"];
    if (!llmStore) {
      return;
    }

    const pending = llmStore.consumePendingOpenInChatter(
      this.props.threadModel,
      this.props.threadId
    );

    if (!pending) {
      return;
    }

    if (this.state.isChattingWithLLM) {
      return;
    }

    this.state.llmThreadId = pending.threadId;

    // v17: Insert thread and set on discuss directly
    const llmThread = this.store.Thread.insert({
      model: "llm.thread",
      id: pending.threadId,
      isLoaded: true,
    });

    if (!this.store.discuss) {
      this.store.discuss = {};
    }
    this.store.discuss.thread = llmThread;

    // v17: Use threadService.fetchData() instead of thread.fetchData()
    await this.threadService.fetchData(llmThread, ["messages"]);

    this.state.isChattingWithLLM = true;

    if (pending.autoGenerate) {
      await llmStore.startLLMStreaming(pending.threadId, null);
    }
  },

  focusComposerWhenReady() {
    requestAnimationFrame(() => {
      const chatterEl = this.rootRef?.el;
      if (chatterEl) {
        chatterEl.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });
      }

      const composerSelectors = [
        ".o-mail-Composer-input",
        ".o-llm-composer-area textarea",
      ];
      const composer = composerSelectors
        .map((sel) => document.querySelector(sel))
        .find((el) => el !== null);

      if (composer) {
        setTimeout(() => {
          composer.scrollIntoView({
            behavior: "smooth",
            block: "center",
          });
          composer.focus();
        }, 300);
      }
    });
  },

  get shouldShowAIButton() {
    return this.props.threadModel && this.props.threadId;
  },

  async onAIChatClick() {
    if (!this.shouldShowAIButton) return;

    if (this.state.isChattingWithLLM) {
      this.state.isChattingWithLLM = false;
      this.state.llmThreadId = null;

      if (this.store.discuss) {
        this.store.discuss.thread = undefined;
      }
    } else {
      try {
        const threadId = await this.ensureLLMThread();
        if (threadId) {
          const llmThread = this.store.Thread.insert({
            model: "llm.thread",
            id: threadId,
            isLoaded: true,
          });

          if (!this.store.discuss) {
            this.store.discuss = {};
          }
          this.store.discuss.thread = llmThread;

          // v17: Use threadService.fetchData() instead of thread.fetchData()
          await this.threadService.fetchData(llmThread, ["messages"]);

          this.state.isChattingWithLLM = true;
          this.state.llmThreadId = threadId;
        }
      } catch (error) {
        console.error("Failed to start AI chat:", error);
        this.notification.add(error.message || "Failed to start AI chat", {
          type: "danger",
        });
      }
    }
  },

  async ensureLLMThread() {
    const existingThreads = await this.orm.searchRead(
      "llm.thread",
      [
        ["model", "=", this.props.threadModel],
        ["res_id", "=", this.props.threadId],
      ],
      ["id"],
      { limit: 1 }
    );

    if (existingThreads.length > 0) {
      return existingThreads[0].id;
    }

    let modelId = null;
    let providerId = null;

    const defaultModels = await this.orm.searchRead(
      "llm.model",
      [
        ["model_use", "in", ["chat", "multimodal"]],
        ["default", "=", true],
        ["active", "=", true],
      ],
      ["id", "provider_id"],
      { limit: 1 }
    );

    if (defaultModels.length > 0) {
      modelId = defaultModels[0].id;
      providerId = defaultModels[0].provider_id[0];
    } else {
      const providers = await this.orm.searchRead(
        "llm.provider",
        [["active", "=", true]],
        ["id"],
        { limit: 1 }
      );

      if (providers.length === 0) {
        throw new Error(
          "No active LLM provider found. Please configure a provider first."
        );
      }

      providerId = providers[0].id;

      const models = await this.orm.searchRead(
        "llm.model",
        [
          ["provider_id", "=", providerId],
          ["model_use", "in", ["chat", "multimodal"]],
          ["active", "=", true],
        ],
        ["id"],
        { limit: 1 }
      );

      if (models.length === 0) {
        throw new Error(
          "No active chat model found. Please configure a model first."
        );
      }

      modelId = models[0].id;
    }

    const threadIds = await this.orm.create("llm.thread", [
      {
        model: this.props.threadModel,
        res_id: this.props.threadId,
        provider_id: providerId,
        model_id: modelId,
      },
    ]);

    return Array.isArray(threadIds) ? threadIds[0] : threadIds;
  },
});
