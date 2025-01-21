/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Timer } from "../timer/timer";

export class TaskList extends Component {
    static template = "task_timer.TaskList";
    static components = { Timer };
    
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            tasks: [],
        });
        
        onWillStart(async () => {
            await this.loadTasks();
        });
    }
    
    async loadTasks() {
        this.state.tasks = await this.orm.call(
            'task.timer.task',
            'search_read',
            [],
            ['name', 'description', 'total_time', 'is_active']
        );
    }
}