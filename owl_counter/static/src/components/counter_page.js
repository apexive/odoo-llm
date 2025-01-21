/** @odoo-module **/

import { Counter } from "./counter/counter";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

// This is like a parent component in React that will be our main page
class CounterPage extends Component {
    static template = "owl_counter.CounterPage";
    static components = { Counter };  // Register Counter as a subcomponent
}

// Register the page as a client action
registry.category("actions").add("owl_counter.action_counter_page", CounterPage);