/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class Timer extends Component {
    static template = "task_timer.Timer";
    static props = {
        taskId: Number,
        onTimerUpdate: Function,
    };
    
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            isRunning: false,
            startTime: null,
            elapsedTime: 0,
        });
        
        onWillStart(async () => {
            // Check if there's an active timer
            const [task] = await this.orm.call(
                'task.timer.task',          // Model name
                'read',                     // Method name
                [[this.props.taskId]],      // Array of record IDs wrapped in another array
                {                           // Options object
                    fields: ['is_active']   // Fields to read
                }
            );
            this.state.isRunning = task.is_active;
        });
    }

    formatDateTime(date) {
        // Format date as YYYY-MM-DD HH:mm:ss
        return date.toLocaleString('sv-SE').replace('T', ' ').split('.')[0];
    }
    
    async startTimer() {
        const now = new Date();
        const result = await this.orm.call('task.timer.entry','create', [{
            task_id: this.props.taskId,
            start_time: this.formatDateTime(now),
        }]);
        this.state.isRunning = true;
        this.props.onTimerUpdate();
    }
    
    async stopTimer() {
        const [activeEntry] = await this.orm.call(
            'task.timer.entry',
            'search_read',
            [[['task_id', '=', this.props.taskId], ['end_time', '=', false]]],
            { fields: ['id'] }
        );
        
        if (activeEntry) {
            const now = new Date();
            // Update the entry with end time
            await this.orm.call(
                'task.timer.entry',
                'write',
                [[activeEntry.id], {
                    end_time: this.formatDateTime(now),
                }]
            );
        }
        
        this.state.isRunning = false;
        this.props.onTimerUpdate();
    }
}