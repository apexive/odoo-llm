/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

export class Counter extends Component {
    static template = "owl_counter.Counter";
    static props = {};
    
    setup() {
        // This is similar to React's useState hook
        this.state = useState({ count: 0 });
    }
    
    increment() {
        this.state.count++;
    }
    
    decrement() {
        this.state.count--;
    }
}