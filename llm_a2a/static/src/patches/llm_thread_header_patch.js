/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { LLMThreadHeader } from "@llm_thread/components/llm_thread_header/llm_thread_header";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";

/**
 * Patch LLMThreadHeader to add A2A agents dropdown
 */
patch(LLMThreadHeader.prototype, {
  setup() {
    super.setup(...arguments);

    // Add A2A-specific state
    this.state.a2aAgents = [];
    this.state.isLoadingA2aAgents = false;

    // Load A2A agents
    this.loadA2aAgents();
  },

  /**
   * Load available A2A agents
   */
  async loadA2aAgents() {
    try {
      this.state.isLoadingA2aAgents = true;
      const agents = await rpc("/llm/a2a/agents", {
        domain: [["state", "=", "connected"]],
      });
      this.state.a2aAgents = agents || [];
    } catch (error) {
      console.error("Error loading A2A agents:", error);
      this.state.a2aAgents = [];
    } finally {
      this.state.isLoadingA2aAgents = false;
    }
  },

  /**
   * Get available A2A agents
   */
  get availableA2aAgents() {
    return this.state.a2aAgents || [];
  },

  /**
   * Get current A2A agents for the thread
   */
  get currentA2aAgents() {
    if (!this.hasActiveThread) return [];

    const agentIds = this.activeThread.a2a_agent_ids || [];
    if (!agentIds.length) return [];

    // Handle different formats: array of objects or array of IDs
    return agentIds
      .map((agent) => {
        if (typeof agent === "object" && agent.id) {
          return (
            this.state.a2aAgents.find((a) => a.id === agent.id) || agent
          );
        }
        return this.state.a2aAgents.find((a) => a.id === agent);
      })
      .filter(Boolean);
  },

  /**
   * Check if an A2A agent is selected
   * @param {Object} agent - Agent object to check
   * @returns {Boolean} True if agent is selected
   */
  isA2aAgentSelected(agent) {
    if (!this.hasActiveThread) return false;

    const agentIds = (this.activeThread.a2a_agent_ids || []).map((a) =>
      typeof a === "object" ? a.id : a
    );
    return agentIds.includes(agent.id);
  },

  /**
   * Toggle A2A agent selection
   * @param {Object} agent - Agent object to toggle
   */
  async toggleA2aAgent(agent) {
    try {
      this.state.isLoadingUpdate = true;

      // Get current agent IDs from the active thread
      const currentAgentIds = (this.activeThread.a2a_agent_ids || []).map(
        (a) => (typeof a === "object" ? a.id : a)
      );

      const newAgentIds = currentAgentIds.includes(agent.id)
        ? currentAgentIds.filter((id) => id !== agent.id)
        : [...currentAgentIds, agent.id];

      // Update via controller
      const result = await rpc(
        `/llm/thread/${this.activeThread.id}/a2a_agents`,
        {
          agent_ids: newAgentIds,
        }
      );

      if (result.success) {
        // Update local state
        this.activeThread.a2a_agent_ids = result.a2a_agent_ids;
      } else {
        this.notification.add(
          result.error || _t("Failed to update A2A agents"),
          { type: "danger" }
        );
      }
    } catch (error) {
      this.notification.add(
        _t("Could not update the A2A agents. Please try again."),
        {
          type: "danger",
        }
      );
      console.error("Error updating A2A agents:", error);
    } finally {
      this.state.isLoadingUpdate = false;
    }
  },
});
