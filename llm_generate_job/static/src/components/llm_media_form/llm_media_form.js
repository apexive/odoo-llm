/** @odoo-module **/

                        import { LLMMediaForm } from "@llm_generate/components/llm_media_form/llm_media_form";
                        import { registerMessagingComponent } from "@mail/utils/messaging_component";
                        import { JsonEditorComponent } from "@web_json_editor/components/json_editor/json_editor";
                        import { LLMFormFieldsView } from "@llm_generate/components/llm_media_form/llm_form_fields_view";
                        import { patch } from '@web/core/utils/patch';

                        patch(LLMMediaForm.prototype, 'llm_job_media_form', {
                            setup() {
                                // Llamar al setup original primero
                                this._super(...arguments);

                                // Inicializamos explícitamente la propiedad
                                this.state.supportsAsyncGeneration = false;
                                console.log("Patch aplicado a LLMMediaForm - Estado inicial:", this.state);

                                // Usar useEffect para detectar cambios en el thread
                                useEffect(
                                    () => {
                                        console.log("useEffect detectó cambio en thread:", this.thread);
                                        if (this.thread) {
                                            // Inspeccionar el thread para entender su estructura
                                            console.log("Thread estructura completa:", this.thread);

                                            // Intentar encontrar el provider_id correctamente
                                            this._checkAsyncGenerationSupport();
                                        }
                                    },
                                    // Dependencias para activar el efecto
                                    () => [this.thread?.id, this.llmModel?.id]
                                );
                            },

                            // Método mejorado para verificar soporte de generación asíncrona
                            async _checkAsyncGenerationSupport() {
                                console.log("_checkAsyncGenerationSupport - thread:", this.thread);

                                if (!this.thread || !this.thread.id) {
                                    console.log("No thread available, supportsAsyncGeneration = false");
                                    this.state.supportsAsyncGeneration = false;
                                    return;
                                }

                                try {
                                    console.log("Llamando a RPC con thread_id:", this.thread.id);
                                     const result = await this.messaging.rpc({
                                        model: "llm.thread",
                                        method: "check_async_generation_support",
                                        args: [this.thread.id],
                                    });
                                    console.log("Resultado:", result);
                                    this.state.supportsAsyncGeneration = result.supports_async;
                                    console.log("supportsAsyncGeneration =", this.state.supportsAsyncGeneration);
                                } catch (error) {
                                    console.warn("Error verificando soporte async:", error);
                                    this.state.supportsAsyncGeneration = false;
                                }
                            },

                            // Implementar onSendJob
                            async onSendJob(event) {
                                event.preventDefault();

                                const validationResult = this._validateFormValues();
                                console.log("Validación:", validationResult);

                                if (!validationResult.isValid) {
                                    this.state.error = validationResult.errors.join("\n");
                                    return;
                                }

                                this.state.isLoading = true;
                                this.state.error = null;



                                try {
                                    const result = await this.messaging.rpc({
                                        route: "/api/llm/thread/submit_async_generation",
                                        params: {
                                            thread_id: this.thread.id,
                                            generation_inputs: validationResult.values,
                                            model_id: this.llmModel?.id
                                        },
                                    });
                                    console.log("Resultado trabajo asíncrono:", result);

                                    if (result.success) {
                                        this.env.services.notification.add(
                                            `🚀 Generation job submitted! Job ID: ${result.job_id}`,
                                            { type: 'success', sticky: false }
                                        );
                                        this.state.error = null;
                                    } else {
                                        this.state.error = result.error || "Failed to submit job.";
                                    }
                                } catch (error) {
                                    console.error("Error:", error);
                                    this.state.error = error.message || "Unexpected error.";
                                } finally {
                                    this.state.isLoading = false;
                                }
                            }
                        });

                        // Necesitas importar useEffect ya que lo estás utilizando en el patch
                        const { Component, useState, onWillStart, useEffect } = owl;

                        console.log("Patch aplicado al componente LLMMediaForm");