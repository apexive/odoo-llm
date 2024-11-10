/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useComponentToModel } from "@mail/component_hooks/use_component_to_model";
import { useRenderedValues } from "@mail/component_hooks/use_rendered_values";
import { useUpdate } from "@mail/component_hooks/use_update";
import { Transition } from "@web/core/transition";

const { onWillPatch, useRef } = owl;

export class LLMMessageList extends Component {
  setup() {
    super.setup();
    useComponentToModel({ fieldName: "component" });
    this._scrollableRef = useRef("scrollable");

    // Track rendered values for scroll management
    this._lastRenderedValues = useRenderedValues(() => {
      const messageListView = this.props.record;
      return {
        messageListView,
        messages: messageListView ? [...messageListView.messages] : [],
        isLoading: messageListView ? messageListView.isLoading : false,
        hasMoreMessages: messageListView
          ? messageListView.hasMoreMessages
          : false,
      };
    });

    this._onScrollThrottled = _.throttle(
      this._onScrollThrottled.bind(this),
      100
    );
    useUpdate({ func: () => this._update() });
    onWillPatch(() => this._willPatch());
  }

  _willPatch() {
    if (!this._scrollableRef.el) {
      return;
    }
    // Save scroll position before patch
    this._willPatchSnapshot = {
      scrollHeight: this._scrollableRef.el.scrollHeight,
      scrollTop: this._scrollableRef.el.scrollTop,
    };
  }

  /**
   * Scroll to bottom of message list
   * @private
   */
  _scrollToEnd() {
    if (!this._scrollableRef.el) {
      return;
    }
    this._scrollableRef.el.scrollTop = this._scrollableRef.el.scrollHeight;
  }

  /**
   * Handle scroll event to load more messages and track scroll position
   * @private
   */
  _onScrollThrottled(ev) {
    if (!this._scrollableRef.el) {
      return;
    }

    const { messageListView } = this._lastRenderedValues();
    if (!messageListView) {
      return;
    }

    // Auto-load more messages when scrolling near top
    if (
      this._scrollableRef.el.scrollTop < 100 &&
      messageListView.hasMoreMessages
    ) {
      messageListView.loadMoreMessages();
    }

    // Update scroll tracking
    messageListView.update({
      scrollHeight: this._scrollableRef.el.scrollHeight,
      scrollTop: this._scrollableRef.el.scrollTop,
      isAtBottom: this._isAtBottom(),
    });
  }

  /**
   * @returns {boolean}
   */
  _isAtBottom() {
    if (!this._scrollableRef.el) {
      return false;
    }
    const { scrollHeight, scrollTop, clientHeight } = this._scrollableRef.el;
    return Math.abs(scrollHeight - scrollTop - clientHeight) <= 1;
  }

  /**
   * Adjust scroll position after updates
   * @private
   */
  _update() {
    const { messageListView, messages } = this._lastRenderedValues();
    if (!messageListView || !this._scrollableRef.el) {
      return;
    }

    // Keep scroll position when loading older messages
    if (this._willPatchSnapshot && messageListView.isLoadingMore) {
      const { scrollHeight: oldScrollHeight, scrollTop: oldScrollTop } =
        this._willPatchSnapshot;
      const newScrollTop =
        this._scrollableRef.el.scrollHeight - oldScrollHeight + oldScrollTop;
      this._scrollableRef.el.scrollTop = newScrollTop;
    }
    // Scroll to bottom for new messages if already at bottom
    else if (messageListView.isAtBottom) {
      this._scrollToEnd();
    }

    this._willPatchSnapshot = undefined;
  }

  /**
   * @private
   */
  onScroll(ev) {
    this._onScrollThrottled(ev);
  }
}

Object.assign(LLMMessageList, {
  components: { Transition },
  props: { record: Object },
  template: "llm.MessageList",
});
