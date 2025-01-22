/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";
import "@mail/models/composer_view";
import session from "web.session";
import { attr } from "@mail/model/model_field";
import { clear } from "@mail/model/model_field_command";
import { sprintf } from "@web/core/utils/strings";
import { Dialog } from "web.Dialog";

registerPatch({
    name: "ComposerView",
    fields: {
        isAiThinking: attr({
            default: false,
        }),
        llmThreadConfig: attr({
            default: null,
        }),
    },
    recordMethods: {
        /**
         * Handle AI button click
         */
        onClickAskAI: async function () {
            console.log('[onClickAskAI] Starting with llmThreadConfig:', this.llmThreadConfig);
            if (!this.llmThreadConfig) {
                console.log('[onClickAskAI] Fetching thread config...');
                await this._fetchLlmConfig();
                console.log('[onClickAskAI] After fetch, llmThreadConfig:', this.llmThreadConfig);
            }

            if (!this.llmThreadConfig) {
                await this._ensureThreadConfig();
            }

            if (this.llmThreadConfig) {
                await this._sendQuestionForAi();
            }
        },
        /**
         * Handle AI config button click
         */
        onClickAIConfig: async function () {
            await this._ensureThreadConfig();
            if (this.llmThreadConfig) {
                this._openConfigDialog();
            }
        },
        /**
         * Ensure thread configuration exists
         * Creates a default configuration if none exists
         */
        async _ensureThreadConfig() {
            if (!this.llmThreadConfig) {
                const defaultConfig = await this._getDefaultConfig();
                if (defaultConfig) {
                    await this._createThreadConfig(defaultConfig);
                } else {
                    // Try to find default chat model
                    const providers = await this._fetchProviders();
                    if (!providers.length) {
                        this.messaging.notify({
                            message: this.env._t(
                                "No AI providers configured. Please contact your administrator."
                            ),
                            type: "warning",
                        });
                        return;
                    }

                    const models = await this._fetchModels(providers[0].id);
                    if (!models.length) {
                        this.messaging.notify({
                            message: this.env._t(
                                "No AI models available for the selected provider."
                            ),
                            type: "warning",
                        });
                        return;
                    }

                    await this._createThreadConfig({
                        provider_id: providers[0].id,
                        model_id: models[0].id,
                    });
                }
                await this._fetchLlmConfig();
            }
        },
        /**
         * Open thread configuration dialog
         */
        _openConfigDialog() {
            this.env.services.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'llm.thread',
                res_id: this.llmThreadConfig.thread_id,
                views: [[false, 'form']],
                target: 'new',
                context: {
                    form_view_ref: 'llm_thread.llm_thread_view_form',
                },
            }, {
                onClose: async () => {
                    await this._fetchLlmConfig();
                },
            });
        },
        /**
         * Fetch LLM thread configuration for the current thread
         */
        async _fetchLlmConfig() {
            console.log('[_fetchLlmConfig] Starting');
            const composer = this.composer;
            if (!composer.thread) {
                console.log('[_fetchLlmConfig] No composer thread, returning');
                return;
            }

            try {
                console.log('[_fetchLlmConfig] Fetching for model:', composer.thread.model, 'id:', composer.thread.id);
                const result = await this.messaging.rpc({
                    route: "/llm/thread/config",
                    params: {
                        model: composer.thread.model,
                        record_id: composer.thread.id,
                    },
                });
                console.log('[_fetchLlmConfig] Result:', result);
                if (!result.error) {
                    this.update({ llmThreadConfig: result });
                    console.log('[_fetchLlmConfig] Config updated');
                }
            } catch (error) {
                console.error("[_fetchLlmConfig] Error:", error);
            }
        },

        /**
         * Get default provider and model configuration
         */
        _getDefaultConfig: async function () {
            try {
                // Search for default chat model
                const defaultModel = await this.messaging.rpc({
                    model: "llm.model",
                    method: "search_read",
                    args: [
                        [
                            ["model_use", "=", "chat"],
                            ["default", "=", true],
                            ["active", "=", true],
                        ],
                        ["id", "name", "provider_id"],
                    ],
                    kwargs: { limit: 1 },
                });

                if (defaultModel.length) {
                    return {
                        providerId: defaultModel[0].provider_id[0],
                        modelId: defaultModel[0].id,
                    };
                }

                // Fallback: get any active chat model
                const anyModel = await this.messaging.rpc({
                    model: "llm.model",
                    method: "search_read",
                    args: [
                        [
                            ["model_use", "=", "chat"],
                            ["active", "=", true],
                        ],
                        ["id", "name", "provider_id"],
                    ],
                    kwargs: { limit: 1 },
                });

                if (anyModel.length) {
                    return {
                        providerId: anyModel[0].provider_id[0],
                        modelId: anyModel[0].id,
                    };
                }

                return null;
            } catch (error) {
                console.error("Failed to get default config:", error);
                return null;
            }
        },

        /**
         * Fetch available LLM providers
         */
        async _fetchProviders() {
            try {
                const result = await this.messaging.rpc({
                    model: "llm.provider",
                    method: "search_read",
                    args: [[["active", "=", true]], ["id", "name"]],
                });
                return result;
            } catch (error) {
                console.error("Failed to fetch providers:", error);
                return [];
            }
        },

        /**
         * Fetch available models for a provider
         */
        async _fetchModels(providerId) {
            try {
                const result = await this.messaging.rpc({
                    model: "llm.model",
                    method: "search_read",
                    args: [
                        [
                            ["provider_id", "=", providerId],
                            ["active", "=", true],
                        ],
                        ["id", "name", "provider_id"],
                    ],
                });
                return result;
            } catch (error) {
                console.error("Failed to fetch models:", error);
                return [];
            }
        },

        /**
         * Create new thread configuration
         */
        async _createThreadConfig(config) {
            console.log('[_createThreadConfig] Starting with:', config);
            try {
                const composer = this.composer;
                const result = await this.messaging.rpc({
                    route: "/llm/thread/create",
                    params: {
                        model: composer.thread.model,
                        record_id: composer.thread.id,
                        provider_id: config.providerId,
                        model_id: config.modelId,
                    },
                });
                console.log('[_createThreadConfig] Result:', result);
                if (result.error) {
                    throw new Error(result.error);
                }

                return result;
            } catch (error) {
                console.error("Failed to create thread config:", error);
                this.messaging.notify({
                    message: this.env._t("Failed to create AI configuration"),
                    type: "danger",
                });
                return null;
            }
        },

        /**
         * Update AI thinking state
         */
        updateIsAiThinking(isAiThinking) {
            this.update({ isAiThinking });
        },

        /**
         * Send question to AI
         */
        async _sendQuestionForAi() {
            this.updateIsAiThinking(true);
            const composer = this.composer;
            const postData = this._getMessageData();

            try {
                composer.update({ isPostingMessage: true });

                // Add LLM specific data
                Object.assign(postData, {
                    subtype_xmlid: "llm_thread.mt_llm_question",
                    llm_thread_id: this.llmThreadConfig.thread_id,
                });

                // Handle reply context
                if (
                    this.threadView?.replyingToMessageView &&
                    this.threadView.thread !== this.messaging.inbox.thread
                ) {
                    postData.parent_id = this.threadView.replyingToMessageView.message.id;
                }

                // Post message
                const params = {
                    post_data: postData,
                    thread_id: composer.thread.id,
                    thread_model: composer.thread.model,
                    context: Object.assign({}, session.user_context),
                };

                const messageData = await this.messaging.rpc({
                    route: "/mail/message/post",
                    params,
                });

                // Handle message posting success
                if (this.messaging.exists()) {
                    const message = this.messaging.models["Message"].insert(
                        this.messaging.models["Message"].convertData(messageData)
                    );

                    // Handle link previews if enabled
                    if (this.messaging.hasLinkPreviewFeature && !message.isBodyEmpty) {
                        this.messaging.rpc(
                            {
                                route: "/mail/link_preview",
                                params: { message_id: message.id },
                            },
                            { shadow: true }
                        );
                    }

                    // Update thread views
                    this._updateThreadViews(message);

                    // Handle chatter specific logic
                    this._handleChatterLogic();

                    // Reset composer
                    if (composer.exists()) {
                        composer._reset();
                    }
                }
            } catch (error) {
                console.error("Failed to send message:", error);
                this.messaging.notify({
                    message: this.env._t("Failed to send message to AI"),
                    type: "danger",
                });
            } finally {
                if (composer.exists()) {
                    composer.update({ isPostingMessage: false });
                }
                this.updateIsAiThinking(false);
            }
        },

        /**
         * Update thread views after message post
         */
        _updateThreadViews(message) {
            for (const threadView of message.originThread.threadViews) {
                threadView.update({ hasAutoScrollOnMessageReceived: true });
                threadView.addComponentHint("message-posted", { message });
            }

            if (this.threadView?.exists()) {
                this.threadView.update({ replyingToMessageView: clear() });
            }
        },

        /**
         * Handle chatter specific logic
         */
        _handleChatterLogic() {
            const chatter = this.chatter;
            if (!chatter?.exists()) return;

            if (chatter.hasParentReloadOnMessagePosted) {
                chatter.reloadParentView();
            }

            const chatterThread = chatter.thread;
            if (chatterThread?.exists()) {
                if (this.exists()) {
                    this.delete();
                }
                chatterThread.fetchData([
                    "followers",
                    "messages",
                    "suggestedRecipients",
                ]);
            }
        },
    },

    lifecycleHooks: {
        _created() {
            this._super();
            this._fetchLlmConfig();
        },
    },
});
