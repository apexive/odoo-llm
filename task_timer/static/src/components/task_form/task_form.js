/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class TaskForm extends Component {
    static template = "task_timer.TaskForm";
    static props = {
        onTaskCreated: { type: Function },
        onClose: { type: Function },
    };
    
    setup() {
        // Initialize our form state
        this.state = useState({
            name: "",
            description: "",
            error: "",
        });
        
        // Get the ORM service for database operations
        this.orm = useService("orm");
    }
    
    // Handle input changes
    updateName(ev) {
        this.state.name = ev.target.value;
    }
    
    updateDescription(ev) {
        this.state.description = ev.target.value;
    }
    
    // Create the task
    async createTask() {
        if (!this.state.name.trim()) {
            this.state.error = "Task name is required";
            return;
        }
        
        try {
            // Create the task using ORM
            await this.orm.call(
                'task.timer.task',
                'create',
                [{
                    name: this.state.name,
                    description: this.state.description,
                }]
            );
            
            // Notify parent component and close form
            this.props.onTaskCreated();
            this.props.onClose();
        } catch (error) {
            this.state.error = "Failed to create task";
            console.error("Task creation error:", error);
        }
    }
}