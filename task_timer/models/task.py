from odoo import models, fields, api

class Task(models.Model):
    _name = 'task.timer.task'
    _description = 'Timer Task'

    name = fields.Char('Task Name', required=True)
    description = fields.Text('Description')
    time_entries = fields.One2many('task.timer.entry', 'task_id', string='Time Entries')
    total_time = fields.Float('Total Time (Hours)', compute='_compute_total_time', store=True)
    is_active = fields.Boolean('Is Active Timer', compute='_compute_is_active')
    
    @api.depends('time_entries.duration')
    def _compute_total_time(self):
        for task in self:
            task.total_time = sum(entry.duration for entry in task.time_entries)
    
    @api.depends('time_entries.end_time')
    def _compute_is_active(self):
        for task in self:
            task.is_active = any(not entry.end_time for entry in task.time_entries)