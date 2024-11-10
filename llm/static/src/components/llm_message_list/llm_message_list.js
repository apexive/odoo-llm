/** @odoo-module **/

import { Component, onWillDestroy, useRef, onWillPatch, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { Transition } from "@web/core/transition";
import { LLMMessage } from "../llm_message/llm_message";

const SCROLL_THRESHOLD = 100; // pixels from bottom to trigger auto-scroll
const LOAD_MORE_THRESHOLD = 50; // pixels from top to trigger loading more
const SCROLL_DEBOUNCE = 100; // ms to debounce scroll events

/**
 * Message list component for LLM chat interface
 */
export class LLMMessageList extends Component {
  setup() {
    this.scrollableRef = useRef("scrollable");
    this.lastMessageCount = 0;
    this.scrollTimeout = null;
    this.isScrolling = false;

    // Setup services
    this.uiService = useService("ui");

    // Bind methods
    this.onScrollThrottled = _.throttle(this._onScroll.bind(this), SCROLL_DEBOUNCE);

    // Setup lifecycle hooks
    onMounted(() => this._scrollToEnd(false));
    onWillPatch(() => this._willPatch());
    onWillDestroy(() => this._cleanup());

    // Setup resize observer
    this._setupResizeObserver();
  }

  /**
   * @returns {Object} The message list record from props
   */
  get messageListView() {
    return this.props.record;
  }

  /**
   * @returns {Array} List of messages to display
   */
  get messages() {
    return this.messageListView.messages || [];
  }

  /**
   * @returns {boolean} Whether list is empty
   */
  get isEmpty() {
    return this.messages.length === 0;
  }

  /**
   * Clean up resources
   * @private
   */
  _cleanup() {
    if (this.scrollTimeout) {
      clearTimeout(this.scrollTimeout);
    }
    if (this.onScrollThrottled?.cancel) {
      this.onScrollThrottled.cancel();
    }
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
  }

  /**
   * Setup resize observer to handle container resizing
   * @private
   */
  _setupResizeObserver() {
    this.resizeObserver = new ResizeObserver(entries => {
      for (const entry of entries) {
        if (entry.target === this.scrollableRef.el) {
          this._maintainScrollPosition();
        }
      }
    });
  }

  /**
   * Store current scroll state before patching
   * @private
   */
  _willPatch() {
    if (!this.scrollableRef.el) return;

    this.patchSnapshot = {
      scrollHeight: this.scrollableRef.el.scrollHeight,
      scrollTop: this.scrollableRef.el.scrollTop,
      clientHeight: this.scrollableRef.el.clientHeight,
      messageCount: this.messages.length,
      isNearBottom: this._isNearBottom(),
    };
  }

  /**
   * Check if scrolled near bottom
   * @private
   * @param {number} threshold Pixels from bottom to consider "near"
   * @returns {boolean}
   */
  _isNearBottom(threshold = SCROLL_THRESHOLD) {
    if (!this.scrollableRef.el) return false;

    const { scrollHeight, scrollTop, clientHeight } = this.scrollableRef.el;
    return scrollHeight - scrollTop - clientHeight <= threshold;
  }

  /**
   * Check if scrolled near top
   * @private
   * @param {number} threshold Pixels from top to consider "near"
   * @returns {boolean}
   */
  _isNearTop(threshold = LOAD_MORE_THRESHOLD) {
    if (!this.scrollableRef.el) return false;
    return this.scrollableRef.el.scrollTop <= threshold;
  }

  /**
   * Scroll to bottom of list
   * @private
   * @param {boolean} smooth Whether to use smooth scrolling
   */
  _scrollToEnd(smooth = true) {
    if (!this.scrollableRef.el) return;

    this.scrollableRef.el.scrollTo({
      top: this.scrollableRef.el.scrollHeight,
      behavior: smooth ? 'smooth' : 'auto'
    });
  }

  /**
   * Maintain relative scroll position after content changes
   * @private
   */
  _maintainScrollPosition() {
    if (!this.scrollableRef.el || !this.patchSnapshot) return;

    const { scrollHeight: oldScrollHeight, scrollTop: oldScrollTop } = this.patchSnapshot;
    const newScrollTop = this.scrollableRef.el.scrollHeight - oldScrollHeight + oldScrollTop;

    this.scrollableRef.el.scrollTop = newScrollTop;
  }

  /**
   * Update scroll position and handling loading more messages
   * @private
   */
  _onScroll() {
    if (!this.scrollableRef.el || !this.messageListView) return;

    const { scrollTop } = this.scrollableRef.el;
    const isAtBottom = this._isNearBottom();
    const isNearTop = this._isNearTop();

    // Update list state
    this.messageListView.updateScroll(scrollTop, isAtBottom);

    // Handle loading more messages
    if (isNearTop &&
        this.messageListView.hasMoreMessages &&
        !this.messageListView.isLoadingMore) {
      this.messageListView.loadMoreMessages();
    }

    // Update scrolling status
    this.isScrolling = true;
    if (this.scrollTimeout) {
      clearTimeout(this.scrollTimeout);
    }
    this.scrollTimeout = setTimeout(() => {
      this.isScrolling = false;
    }, 150);
  }

  /**
   * Handle scroll event
   * @param {Event} ev Scroll event
   */
  onScroll(ev) {
    this.onScrollThrottled();
  }

  /**
   * Component update hook
   */
  _update() {
    if (!this.scrollableRef.el || !this.messageListView) return;

    const currentMessageCount = this.messages.length;
    const isNewMessage = currentMessageCount > this.lastMessageCount;
    const wasNearBottom = this.patchSnapshot?.isNearBottom;

    // Handle scroll position
    if (this.messageListView.isLoadingMore) {
      this._maintainScrollPosition();
    } else if (isNewMessage && (wasNearBottom || this.messageListView.isAtBottom)) {
      this._scrollToEnd(!this.patchSnapshot);
    }

    this.lastMessageCount = currentMessageCount;
    this.patchSnapshot = undefined;
  }
}

LLMMessageList.components = {
  Transition,
  LLMMessage,
};

LLMMessageList.template = "llm.MessageList";

LLMMessageList.props = {
  record: {
    type: Object,
    required: true,
  },
  className: {
    type: String,
    optional: true
  }
};

// Register the component
registry.category("components").add("LLMMessageList", LLMMessageList);
