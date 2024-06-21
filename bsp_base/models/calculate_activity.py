from odoo import models, fields, api, _
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class CalculateActivity(models.AbstractModel):
    _name = 'calculate.activity'
    _description = 'Calculate Activity'

    activity_start_date = fields.Datetime(
        string='Activity Start',
        readonly=True,
        copy=False,
        track_visibility='onchange'
    )
    activity_end_date = fields.Datetime(
        string='Activity End',
        readonly=True,
        copy=False,
        track_visibility='onchange'
    )
    total_activity = fields.Char(
        string='Total Activity',
        compute='_get_total_activity',
        track_visibility='onchange'
    )

    @api.multi
    def start_activity(self, start_date=False):
        for rec in self:
            rec.activity_start_date = start_date if start_date else datetime.now()

    @api.multi
    def end_activity(self, end_date=False):
        for rec in self:
            if not rec.activity_start_date:
                rec.activity_start_date = end_date if end_date else datetime.now()
            rec.activity_end_date = end_date if end_date else datetime.now()

    @api.multi
    def reset_activity(self, start_date=False):
        for rec in self:
            if rec.activity_end_date:
                rec.activity_end_date = False
            rec.activity_start_date = start_date if start_date else datetime.now()

    @api.depends('activity_start_date', 'activity_end_date')
    def _get_total_activity(self):
        for rec in self:
            total_activity = ''
            if rec.activity_end_date:
                difference = relativedelta(rec.activity_end_date, rec.activity_start_date)
                days = difference.days
                hours = difference.hours
                minutes = difference.minutes
                seconds = difference.seconds
                if days:
                    total_activity += str(days) + ' Days '
                if hours:
                    total_activity += str(hours) + ' Hours '
                if minutes:
                    total_activity += str(minutes) + ' Minutes '
                if seconds:
                    total_activity += str(seconds) + ' Seconds'
                rec.total_activity = total_activity
