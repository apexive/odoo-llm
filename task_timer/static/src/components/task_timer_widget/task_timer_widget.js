/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class TaskTimerWidget extends Component {
    static template = "task_timer.TaskTimerWidget";
    
    setup() {
        // Services we'll need
        this.orm = useService("orm");
        this.notification = useService("notification");
        
        // State management
        this.state = useState({
            isRunning: false,
            startTime: null,
            elapsedTime: '00:00:00',
            currentEntryId: null
        });
        
        // Timer interval reference
        this.timerInterval = null;
        
        // Initial setup
        onWillStart(async () => {
            await this.checkTimerStatus();
        });
        
        // Cleanup
        onWillDestroy(() => {
            if (this.timerInterval) {
                clearInterval(this.timerInterval);
            }
        });
    }
    
    // Format time for display
    formatTime(seconds) {
        const hrs = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    
    // Update elapsed time display
    updateElapsedTime() {
        if (this.state.startTime) {
            const elapsed = Math.floor((new Date() - new Date(this.state.startTime)) / 1000);
            this.state.elapsedTime = this.formatTime(elapsed);
        }
    }
    
    // Check if there's an active timer
    async checkTimerStatus() {
        const activeEntries = await this.orm.call(
            'task.timer.entry',
            'search_read',
            [[['task_id', '=', this.env.model.root.resId], ['end_time', '=', false]]],
            { fields: ['id', 'start_time'] }
        );
        
        if (activeEntries.length > 0) {
            this.state.isRunning = true;
            this.state.startTime = activeEntries[0].start_time;
            this.state.currentEntryId = activeEntries[0].id;
            this.startTimeUpdates();
        }
    }
    
    // Start timer updates
    startTimeUpdates() {
        this.timerInterval = setInterval(() => this.updateElapsedTime(), 1000);
    }
    
    // Format datetime for Odoo
    formatDateTime(date) {
        return date.toLocaleString('sv-SE').replace('T', ' ').split('.')[0];
    }
    
    // Start the timer
    async startTimer() {
        const now = new Date();
        const result = await this.orm.call(
            'task.timer.entry',
            'create',
            [{
                task_id: this.env.model.root.resId,
                start_time: this.formatDateTime(now),
            }]
        );
        
        this.state.isRunning = true;
        this.state.startTime = now;
        this.state.currentEntryId = result;
        this.startTimeUpdates();
        
        // Refresh the form view to update time entries
        await this.env.model.root.load();
        
        this.notification.add("Timer started", { type: "success" });
    }
    
    // Stop the timer
    async stopTimer() {
        if (this.state.currentEntryId) {
            await this.orm.call(
                'task.timer.entry',
                'write',
                [[this.state.currentEntryId], {
                    end_time: this.formatDateTime(new Date())
                }]
            );
        }
        
        clearInterval(this.timerInterval);
        this.state.isRunning = false;
        this.state.startTime = null;
        this.state.currentEntryId = null;
        this.state.elapsedTime = '00:00:00';
        
        // Refresh the form view
        await this.env.model.root.load();
        
        this.notification.add("Timer stopped", { type: "success" });
    }
}

// Register the widget
registry.category("view_widgets").add("task_timer_widget", TaskTimerWidget);