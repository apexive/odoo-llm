/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Timer } from "../timer/timer";
import { TaskForm } from "../task_form/task_form";

export class TaskList extends Component {
    static template = "task_timer.TaskList";
    static components = { Timer, TaskForm };
    
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            tasks: [],
            showCreateForm: false,
        });
        
        onWillStart(async () => {
            await this.loadTasks();
        });
    }
    
    async loadTasks() {
        this.state.tasks = await this.orm.call(
            'task.timer.task',
            'search_read',
            [[]], // Empty domain to get all tasks
            {
                fields: ['name', 'description', 'total_time', 'is_active']
            }
        );
    }
    
    // Toggle create form visibility
    toggleCreateForm() {
        this.state.showCreateForm = !this.state.showCreateForm;
    }
    
    // Handle task creation success
    async handleTaskCreated() {
        await this.loadTasks();
    }
}
