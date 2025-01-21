/** @odoo-module **/

import { Component } from "@odoo/owl";
import { TaskList } from "../task_list/task_list";
import { registry } from "@web/core/registry";

export class TimerDashboard extends Component {
    static template = "task_timer.TimerDashboard";
    static components = { TaskList };
}

// Register the dashboard as a client action
registry.category("actions").add("task_timer.dashboard", TimerDashboard);