/** @odoo-module **/

import { Component, onWillDestroy, useRef, onWillPatch } from "@odoo/owl";
import { useComponentToModel } from "@web/core/utils/component_to_model";
import { useUpdate } from "@web/core/utils/update";
import { Transition } from "@web/core/transition";
import { LLMMessage } from "../llm_message/llm_message";

const SCROLL_THRESHOLD = 100; // pixels from bottom to trigger auto-scroll
const LOAD_MORE_THRESHOLD = 50; // pixels from top to trigger loading more

export class LLMMessageList extends Component {
  setup() {
    super.setup();
    useComponentToModel({ fieldName: "component" });
    this._scrollableRef = useRef("scrollable");

    // Scroll management
    this._lastMessageCount = 0;
    this._scrollTimeout = null;
    this._isScrolling = false;

    // Bind methods
    this._onScrollThrottled = _.throttle(this._onScrollThrottled.bind(this), 100);

    // Setup hooks
    useUpdate({ func: () => this._update() });
    onWillPatch(() => this._willPatch());
    onWillDestroy(() => this._cleanup());
  }

  _cleanup() {
    if (this._scrollTimeout) {
      clearTimeout(this._scrollTimeout);
    }
    if (this._onScrollThrottled.cancel) {
      this._onScrollThrottled.cancel();
    }
  }

  _willPatch() {
    if (!this._scrollableRef.el) return;

    this._willPatchSnapshot = {
      scrollHeight: this._scrollableRef.el.scrollHeight,
      scrollTop: this._scrollableRef.el.scrollTop,
      clientHeight: this._scrollableRef.el.clientHeight,
      messageCount: this.props.record.messages.length,
    };
  }

  _isNearBottom(threshold = SCROLL_THRESHOLD) {
    if (!this._scrollableRef.el) return false;

    const { scrollHeight, scrollTop, clientHeight } = this._scrollableRef.el;
    return scrollHeight - scrollTop - clientHeight <= threshold;
  }

  _isNearTop(threshold = LOAD_MORE_THRESHOLD) {
    if (!this._scrollableRef.el) return false;
    return this._scrollableRef.el.scrollTop <= threshold;
  }

  _scrollToEnd(smooth = true) {
    if (!this._scrollableRef.el) return;

    this._scrollableRef.el.scrollTo({
      top: this._scrollableRef.el.scrollHeight,
      behavior: smooth ? 'smooth' : 'auto'
    });
  }

  _maintainScrollPosition() {
    if (!this._scrollableRef.el || !this._willPatchSnapshot) return;

    const {
      scrollHeight: oldScrollHeight,
      scrollTop: oldScrollTop
    } = this._willPatchSnapshot;

    const newScrollTop = this._scrollableRef.el.scrollHeight - oldScrollHeight + oldScrollTop;
    this._scrollableRef.el.scrollTop = newScrollTop;
  }

  _update() {
    if (!this._scrollableRef.el || !this.props.record) return;

    const currentMessageCount = this.props.record.messages.length;
    const isNewMessage = currentMessageCount > this._lastMessageCount;
    const wasNearBottom = this._willPatchSnapshot?.isNearBottom;

    // Handle scroll position
    if (this.props.record.isLoadingMore) {
      this._maintainScrollPosition();
    } else if (isNewMessage && (wasNearBottom || this.props.record.isAtBottom)) {
      this._scrollToEnd(!this._willPatchSnapshot); // Smooth scroll only if not initial load
    }

    // Update tracking variables
    this._lastMessageCount = currentMessageCount;
    this._willPatchSnapshot = undefined;
  }

  _onScrollThrottled() {
    if (!this._scrollableRef.el || !this.props.record) return;

    const { scrollHeight, scrollTop, clientHeight } = this._scrollableRef.el;
    const isAtBottom = this._isNearBottom();
    const isNearTop = this._isNearTop();

    // Update record state
    this.props.record.update({
      scrollHeight,
      scrollTop,
      isAtBottom,
      hasUnreadMessages: !isAtBottom && this._lastMessageCount < this.props.record.messages.length
    });

    // Handle loading more messages
    if (isNearTop && this.props.record.hasMoreMessages && !this.props.record.isLoadingMore) {
      this.props.record.loadMoreMessages();
    }

    // Clear scrolling status after delay
    if (this._scrollTimeout) {
      clearTimeout(this._scrollTimeout);
    }
    this._scrollTimeout = setTimeout(() => {
      this._isScrolling = false;
    }, 150);
  }

  onScroll(ev) {
    this._isScrolling = true;
    this._onScrollThrottled();
  }
}

LLMMessageList.components = {
  Transition,
  LLMMessage,
};

LLMMessageList.props = {
  record: Object,
  className: { type: String, optional: true },
};

LLMMessageList.template = "llm.MessageList";
