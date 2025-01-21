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
                'task.timer.task',
                'read',
                [this.props.taskId],
                ['is_active']
            );
            this.state.isRunning = task.is_active;
        });
    }
    
    async startTimer() {
        const result = await this.orm.call('task.timer.entry','create', [{
            task_id: this.props.taskId,
            start_time: new Date(),
        }]);
        this.state.isRunning = true;
        this.props.onTimerUpdate();
    }
    
    async stopTimer() {
        const [entry] = await this.orm.call(
            'task.timer.entry',
            'search_read',
            [['task_id', '=', this.props.taskId], ['end_time', '=', false]],
            ['id']
        );
        
        if (entry) {
            await this.orm.call('task.timer.entry', 'write', [entry.id], {
                end_time: new Date(),
            });
        }
        
        this.state.isRunning = false;
        this.props.onTimerUpdate();
    }
}