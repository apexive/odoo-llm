from odoo import models, fields, api
from datetime import datetime

class TimeEntry(models.Model):
    _name = 'task.timer.entry'
    _description = 'Time Entry'
    
    task_id = fields.Many2one('task.timer.task', string='Task', required=True)
    start_time = fields.Datetime('Start Time', default=fields.Datetime.now)
    end_time = fields.Datetime('End Time')
    duration = fields.Float('Duration (Hours)', compute='_compute_duration', store=True)
    
    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for entry in self:
            if entry.end_time and entry.start_time:
                duration = (entry.end_time - entry.start_time).total_seconds() / 3600
                entry.duration = round(duration, 2)
            else:
                entry.duration = 0