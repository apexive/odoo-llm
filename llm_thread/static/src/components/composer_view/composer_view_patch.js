/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";
import "@mail/models/composer_view";
import session from "web.session";
import { attr } from "@mail/model/model_field";
import { clear } from "@mail/model/model_field_command";

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
         * Common error notification handler
         */
        _notifyError(message, type = "warning") {
            this.messaging.notify({
                message: this.env._t(message),
                type,
            });
        },

        /**
         * Common RPC call handler with error handling
         */
        async _makeRPCCall(route, params) {
            try {
                const result = await this.messaging.rpc({
                    route,
                    params,
                });
                if (result.error) {
                    throw new Error(result.error);
                }
                return result;
            } catch (error) {
                console.error(`[${route}] Error:`, error);
                throw error;
            }
        },

        /**
         * Validate provider and model availability
         */
        async _validateProviderAndModel() {
            const providers = await this._fetchProviders();
            if (!providers.length) {
                this._notifyError("No AI providers configured. Please contact your administrator.");
                return null;
            }

            const models = await this._fetchModels(providers[0].id);
            if (!models.length) {
                this._notifyError("No AI models available for the selected provider.");
                return null;
            }

            return {
                provider_id: providers[0].id,
                model_id: models[0].id,
            };
        },

        /**
         * Handle AI button click
         */
        onClickAskAI: async function () {
            if (!this.llmThreadConfig) {
                await this._fetchLlmThread();
            }

            if (!this.llmThreadConfig) {
                await this._ensureLLMThreadExists();
            }

            if (this.llmThreadConfig) {
                await this._sendQuestionForAi();
            }
        },

        /**
         * Handle AI config button click
         */
        onClickAIConfig: async function () {
            await this._ensureLLMThreadExists();
            if (this.llmThreadConfig) {
                this._openLLMThreadEditDialog();
            }
        },

        /**
         * Ensure thread LLMThread exists for this mail.thread
         */
        async _ensureLLMThreadExists() {
            if (!this.llmThreadConfig) {
                const defaultConfig = await this._getDefaultConfig();
                if (defaultConfig) {
                    await this._createLLMThread(defaultConfig);
                } else {
                    const config = await this._validateProviderAndModel();
                    if (config) {
                        await this._createLLMThread(config);
                    }
                }
                await this._fetchLlmThread();
            }
        },

        /**
         * Open LLMThread edit dialog
         */
        _openLLMThreadEditDialog() {
            this.env.services.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'llm.thread',
                res_id: this.llmThreadConfig.thread_id,
                views: [[false, 'form']],
                target: 'new',
                context: {
                },
            }, {
                onClose: async () => {
                    await this._fetchLlmThread();
                },
            });
        },

        /**
         * Fetch LLM thread for the current user's mail.thread
         */
        async _fetchLlmThread() {
            const composer = this.composer;
            if (!composer.thread) {
                return;
            }

            try {
                const result = await this._makeRPCCall("/llm/thread/user", {
                    record_model_name: composer.thread.model,
                    record_id: composer.thread.id,
                });
                this.update({ llmThreadConfig: result });
            } catch (error) {
                // Silent fail as this is just a check
            }
        },

        /**
         * Get default provider and model configuration
         */
        async _getDefaultConfig() {
            try {
                return await this._makeRPCCall("/llm/default/config", {});
            } catch (error) {
                return null;
            }
        },

        /**
         * Fetch available LLM providers
         */
        async _fetchProviders() {
            try {
                const result = await this._makeRPCCall("/llm/providers", {});
                return result.providers || [];
            } catch (error) {
                this._notifyError("Failed to fetch providers");
                return [];
            }
        },

        /**
         * Fetch available models for a provider
         */
        async _fetchModels(providerId) {
            try {
                const result = await this._makeRPCCall("/llm/models", {
                    provider_id: providerId,
                });
                return result.models || [];
            } catch (error) {
                this._notifyError("Failed to fetch models");
                return [];
            }
        },

        /**
         * Create new LLMThread
         */
        async _createLLMThread(config) {
            try {
                const composer = this.composer;
                return await this._makeRPCCall("/llm/thread/create", {
                    model: composer.thread.model,
                    record_id: composer.thread.id,
                    provider_id: config.provider_id,
                    model_id: config.model_id,
                });
            } catch (error) {
                this._notifyError("Failed to create LLMThread", "danger");
                return null;
            }
        },

        /**
         * Update AI thinking state
         */
        updateIsAiThinking(isAiThinking) {
            if (this.exists()) {
                this.update({ isAiThinking });
            }
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
            this._fetchLlmThread();
        },
    },
});
