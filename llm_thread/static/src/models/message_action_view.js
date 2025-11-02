/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registerPatch } from "@mail/model/model_core";

// 3. Patch MessageActionView for visual representation AND CLICK HANDLING
registerPatch({
  name: "MessageActionView",
  fields: {
    // Example of how to override a field via registerPatch
    classNames: {
      compute() {
        const messageAction = this.messageAction;
        if (!messageAction) return "";

        if (messageAction.messageActionListOwnerAsThumbUp) {
          const message = messageAction.messageActionListOwnerAsThumbUp.message;
          const isVoted = message && message.user_vote === 1;
          // Use outlined icon if not voted, solid + color if voted
          const iconClass = isVoted
            ? "fa-thumbs-up text-primary fw-bold"
            : "fa-thumbs-o-up";
          return `${this.paddingClassNames} fa fa-lg ${iconClass}`;
        }
        if (messageAction.messageActionListOwnerAsThumbDown) {
          const message =
            messageAction.messageActionListOwnerAsThumbDown.message;
          const isVoted = message && message.user_vote === -1;
          // Use outlined icon if not voted, solid + color if voted
          const iconClass = isVoted
            ? "fa-thumbs-down text-primary fw-bold"
            : "fa-thumbs-o-down";
          return `${this.paddingClassNames} fa fa-lg ${iconClass}`;
        }

        // If not our actions, call the original compute
        // This will handle core icons (delete, edit, star, etc.) AND padding.
        return this._super();
      },
    },
    title: {
      compute() {
        const messageAction = this.messageAction;
        if (!messageAction) return "";

        if (messageAction.messageActionListOwnerAsThumbUp) {
          return _t("Thumb Up");
        }
        if (messageAction.messageActionListOwnerAsThumbDown) {
          return _t("Thumb Down");
        }
        // Let original handle others (delete, edit, star, etc.)
        return this._super();
      },
    },
  },
  recordMethods: {
    async onClick(ev) {
      const messageAction = this.messageAction;
      let message;
      let newVote;

      if (messageAction.messageActionListOwnerAsThumbUp) {
        message = messageAction.messageActionListOwnerAsThumbUp.message;
        newVote = message.user_vote === 1 ? 0 : 1;
      } else if (messageAction.messageActionListOwnerAsThumbDown) {
        message = messageAction.messageActionListOwnerAsThumbDown.message;
        newVote = message.user_vote === -1 ? 0 : -1;
      } else {
        return this._super(ev); // Not a vote action
      }

      if (!message) {
        return; // Should not happen
      }

      const currentVote = message.user_vote;
      // Optimistically update the UI for a responsive feel
      message.update({ user_vote: newVote });

      try {
        // Use the ORM service to call the instance method
        await this.env.services.orm.call("mail.message", "set_user_vote", [
          [message.id],
          newVote,
        ]);
      } catch (error) {
        // On failure, revert the UI change and notify the user
        message.update({ user_vote: currentVote });
        console.error("Failed to record vote:", error);
        this.env.services.notification.add(
          _t("Failed to record vote: ") +
            (error.data?.message || error.message),
          { type: "danger" }
        );
      }
    },
  },
});
