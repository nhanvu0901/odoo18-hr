from odoo import models, fields, api
from datetime import datetime, date
import json


class HROnboardingReport(models.TransientModel):
    _name = 'hr.onboarding.report'
    _description = 'HR Onboarding/Offboarding Report'

    date_from = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: date.today().replace(month=1, day=1)
    )
    date_to = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.today
    )
    department_ids = fields.Many2many(
        'hr.department',
        string='Departments',
        help='Leave empty to include all departments'
    )

    @api.model
    def get_report_data(self, date_from, date_to, department_ids=None):
        domain = []

        if department_ids:
            domain.append(('department_id', 'in', department_ids))
        employees = self.env['hr.employee'].with_context(active_test=False).search(domain)

        report_data = []
        onboarding_stats = {}
        offboarding_stats = {}

        for employee in employees:
            if employee.create_date and employee.create_date.date():
                hire_date = employee.create_date.date()
                if date_from <= hire_date <= date_to:
                    dept_name = employee.department_id.name or 'No Department'
                    onboarding_stats[dept_name] = onboarding_stats.get(dept_name, 0) + 1

            departure_date = None
            if hasattr(employee, 'departure_date') and employee.departure_date:
                departure_date = employee.departure_date
            elif not employee.active:
                last_contract = self.env['hr.contract'].search([
                    ('employee_id', '=', employee.id)
                ], order='date_end desc', limit=1)
                if last_contract and last_contract.date_end:
                    departure_date = last_contract.date_end
                else:
                    departure_date = employee.write_date.date() if employee.write_date else None

            if departure_date and date_from <= departure_date <= date_to:
                dept_name = employee.department_id.name or 'No Department'
                offboarding_stats[dept_name] = offboarding_stats.get(dept_name, 0) + 1

            start_date = employee.create_date.date() if employee.create_date else None
            end_date = departure_date
            if end_date:
                if end_date > date_to:
                    report_data.append({
                        'employee_name': employee.name,
                        'department': employee.department_id.name or 'No Department',
                        'job_title': employee.job_title or employee.job_id.name or '',
                        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
                        'end_date': end_date.strftime('%Y-%m-%d') if end_date else 'Active',
                    })
            else:
                if (start_date and date_from <= start_date <= date_to):
                    report_data.append({
                        'employee_name': employee.name,
                        'department': employee.department_id.name or 'No Department',
                        'job_title': employee.job_title or employee.job_id.name or '',
                        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
                        'end_date': end_date.strftime('%Y-%m-%d') if end_date else 'Active',
                    })

        return {
            'employee_data': report_data,
            'onboarding_stats': onboarding_stats,
            'offboarding_stats': offboarding_stats,
        }

    def action_generate_report(self):

        department_ids = self.department_ids.ids if self.department_ids else None
        report_data = self.get_report_data(self.date_from, self.date_to, department_ids)

        return {
            'type': 'ir.actions.client',
            'tag': 'hr_onboarding_report_action',
            'context': {
                'report_data': report_data,
                'date_from': self.date_from.strftime('%Y-%m-%d'),
                'date_to': self.date_to.strftime('%Y-%m-%d'),
                'departments': [d.name for d in self.department_ids] if self.department_ids else ['All Departments'],
            }
        }
