from datetime import datetime, timedelta
from odoo import api, fields, models
import logging

logger = logging.getLogger(__name__)


class NotificationCertificate(models.Model):
    _name = 'notification.certificate'
    _description = 'Notification Certificate'
    _rec_name = 'name'

    name = fields.Char('Name', required=True, default='Certificate')

    @api.model
    def process_certificate(self):
        logger.info("Starting certificate processing...")
        today = fields.Date.today()
        thirty_days_from_now = today + timedelta(days=30)

        records = self.env['hr.resume.line'].search([
            ('display_type', '=', 'certification'),
            ('date_end', '>', today),
            ('date_end', '<=', thirty_days_from_now)
        ])

        activity_type = self.env.ref('mail.mail_activity_data_warning', raise_if_not_found=False)
        if not activity_type:
            logger.warning("No suitable activity type found.")
            return False

        for record in records:
            logger.info(f"Processing record: {record.name if hasattr(record, 'name') else record.id}")
            employee = record.employee_id
            if not employee:
                continue

            manager = employee.parent_id
            if not manager:
                continue
            if not manager.user_id:
                continue

            days_until_expiry = (record.date_end - today).days

            if days_until_expiry > 0:
                notification_summary = f"{employee.name}: {record.name} - expires in {days_until_expiry} days."
            else:
                notification_summary = f"{employee.name}: {record.name} - expired"

            existing = self.env['mail.activity'].search([
                ('summary', '=', notification_summary),
                ('user_id', '=', employee.parent_id.user_id.id)
            ], limit=1)

            if not existing:
                self.env['mail.activity'].create({
                    'summary': notification_summary,
                    'activity_type_id': activity_type.id,
                    'note': f'Certification Expiry Notification\n\n'
                            f'Employee: {employee.name}\n'
                            f'Manager: {manager.name}\n'
                            f'Certification: {record.name}\n'
                            f'Expiry Date: {record.date_end.strftime("%B %d, %Y")}\n'
                            f'Days Remaining: {days_until_expiry} days\n'
                            f'Notification Sent: {today.strftime("%B %d, %Y")}\n\n'
                            f'Please ensure your team member renews this certification before expiry to maintain compliance.',
                    'res_model_id': self.env['ir.model']._get_id('hr.employee'),
                    'res_id': employee.id,
                    'user_id': manager.user_id.id,
                    'date_deadline': record.date_end
                })

        return True
