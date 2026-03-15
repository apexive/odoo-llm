/** @odoo-module **/

import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";

/**
 * Patch Thread model to properly handle llm.thread URLs
 *
 * v17 adaptations:
 * - No @web/core/browser/router import - use window.history.replaceState
 * - No thread.setAsDiscussThread() - use mailStore.discuss.thread = thread
 */
patch(Thread.prototype, {
  /**
   * Update action context with active_id
   * @param {String} activeId - Active ID to set
   */
  _updateActionContext(activeId) {
    if (
      !this._store?.action_discuss_id ||
      !this._store.env?.services?.action?.currentController?.action
    ) {
      return;
    }

    const currentAction =
      this._store.env.services.action.currentController.action;
    if (currentAction.id !== this._store.action_discuss_id) {
      return;
    }

    if (!currentAction.context) {
      currentAction.context = {};
    }
    currentAction.context.active_id = activeId;
  },

  /**
   * Override setActiveURL to handle llm.thread model
   */
  setActiveURL() {
    // Handle llm.thread model specifically
    if (this.model === "llm.thread") {
      try {
        const activeId = `llm.thread_${this.id}`;

        // v17: Use window.history.replaceState instead of router.pushState
        const url = new URL(window.location.href);
        url.searchParams.set("active_id", activeId);
        window.history.replaceState({}, "", url.toString());

        // Update action context if available
        this._updateActionContext(activeId);
      } catch (error) {
        console.warn("Error updating URL for LLM thread:", error);
      }
    } else {
      super.setActiveURL();
    }
  },
});
