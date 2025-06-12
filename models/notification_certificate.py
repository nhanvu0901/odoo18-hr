from datetime import datetime, timedelta
from odoo import api, fields, models
import logging

logger = logging.getLogger(__name__)


class CertificateNotificationRecord(models.Model):
    """Custom model to handle certificate notifications with consistent redirect behavior"""
    _name = 'certificate.notification.record'
    _description = 'Certificate Notification Record'
    _inherit = ['mail.thread']
    _rec_name = 'name'

    display_name = fields.Char('Name', compute='_compute_display_name', store=True)
    name = fields.Char('Name', compute='_compute_display_name', store=True)  # Fallback for mail templates
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    certificate_id = fields.Many2one('hr.resume.line', string='Certificate', required=True)
    expiry_date = fields.Date('Expiry Date')
    days_remaining = fields.Integer('Days Remaining', compute='_compute_days_remaining', store=True)

    @api.depends('employee_id', 'certificate_id')
    def _compute_display_name(self):
        for record in self:
            try:
                if record.employee_id and record.certificate_id and hasattr(record.certificate_id, 'id'):
                    # Use display_name which is more reliable than name
                    employee_name = record.employee_id.name or "Unknown Employee"
                    # Try different possible name fields for the certificate
                    certificate_name = (
                            getattr(record.certificate_id, 'name', None) or
                            getattr(record.certificate_id, 'display_name', None) or
                            getattr(record.certificate_id, 'description', None) or
                            f"Certificate {record.certificate_id.id}"
                    )
                    computed_name = f"{employee_name} - {certificate_name}"
                    record.display_name = computed_name
                    record.name = computed_name  # Set both for mail template compatibility
                else:
                    record.display_name = "Certificate Notification"
                    record.name = "Certificate Notification"
            except Exception as e:
                logger.warning(f"Error computing display_name: {e}")
                record.display_name = "Certificate Notification"
                record.name = "Certificate Notification"

    @api.depends('expiry_date')
    def _compute_days_remaining(self):
        today = fields.Date.today()
        for record in self:
            if record.expiry_date:
                record.days_remaining = (record.expiry_date - today).days
            else:
                record.days_remaining = 0

    def action_view_certificate(self):
        """Action that redirects to the certificate list filtered for this employee"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Certificates - {self.employee_id.name}',
            'res_model': 'hr.resume.line',
            'view_mode': 'list,form',
            'domain': [
                ('employee_id', '=', self.employee_id.id),
                ('display_type', '=', 'certification')
            ],
            'context': {
                'default_employee_id': self.employee_id.id,
                'default_display_type': 'certification'
            },
            'target': 'current',
        }


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

        # Check if hr.resume.line model exists (Skills Management must be enabled)
        if 'hr.resume.line' not in self.env:
            logger.error(
                "hr.resume.line model not found. Please enable Skills Management in Employees app → Configuration → Settings")
            return False

        # Try different possible field names for the end date
        end_date_field = None
        possible_end_date_fields = ['date_end', 'end_date', 'date_to', 'validity_end']

        resume_model = self.env['hr.resume.line']
        for field_name in possible_end_date_fields:
            if field_name in resume_model._fields:
                end_date_field = field_name
                logger.info(f"Found end date field: {field_name}")
                break

        if not end_date_field:
            logger.error("Could not find end date field in hr.resume.line model")
            return False

        # Search for certifications expiring in the next 30 days
        records = self.env['hr.resume.line'].search([
            ('display_type', '=', 'certification'),
            (end_date_field, '>', today),
            (end_date_field, '<=', thirty_days_from_now)
        ])

        activity_type = self.env.ref('mail.mail_activity_data_warning', raise_if_not_found=False)
        if not activity_type:
            logger.warning("No suitable activity type found.")
            return False

        for record in records:
            # Skip if record is not valid
            if not record or not hasattr(record, 'id') or not record.id:
                logger.warning("Skipping invalid certificate record")
                continue

            # Get certificate name safely
            certificate_name = (
                    getattr(record, 'name', None) or
                    getattr(record, 'display_name', None) or
                    getattr(record, 'description', None) or
                    f"Certificate {record.id}"
            )
            logger.info(f"Processing record: {certificate_name}")

            employee = record.employee_id
            if not employee or not hasattr(employee, 'id') or not employee.id:
                logger.warning(f"Skipping certificate {certificate_name} - no valid employee")
                continue

            manager = employee.parent_id
            if not manager or not hasattr(manager, 'id') or not manager.id:
                logger.warning(f"Skipping certificate {certificate_name} - no manager for {employee.name}")
                continue
            if not manager.user_id:
                logger.warning(f"Skipping certificate {certificate_name} - manager {manager.name} has no user")
                continue

            # Get the expiry date using the correct field
            expiry_date = getattr(record, end_date_field)
            if not expiry_date:
                logger.warning(f"Skipping certificate {certificate_name} - no expiry date")
                continue

            days_until_expiry = (expiry_date - today).days
            notification_summary = f"Team Member {employee.name}: {certificate_name} - expires in {days_until_expiry} days"

            # Create or get notification record
            try:
                notification_record = self.env['certificate.notification.record'].search([
                    ('employee_id', '=', employee.id),
                    ('certificate_id', '=', record.id)
                ], limit=1)

                if not notification_record:
                    notification_record = self.env['certificate.notification.record'].create({
                        'employee_id': employee.id,
                        'certificate_id': record.id,
                        'expiry_date': expiry_date,  # Set the expiry date manually
                    })

                # Ensure the notification record is valid before creating activity
                if not notification_record or not hasattr(notification_record, 'id') or not notification_record.id:
                    logger.error(f"Failed to create valid notification record for {certificate_name}")
                    continue

            except Exception as e:
                logger.error(f"Error creating notification record for {certificate_name}: {e}")
                continue

            # Check for existing activity
            existing = self.env['mail.activity'].search([
                ('res_model_id', '=', self.env['ir.model']._get_id('certificate.notification.record')),
                ('res_id', '=', notification_record.id),
                ('user_id', '=', manager.user_id.id),
                ('summary', '=', notification_summary)
            ], limit=1)

            if not existing:
                try:
                    activity = self.env['mail.activity'].create({
                        'summary': notification_summary,
                        'activity_type_id': activity_type.id,
                        'note': f'Certification Expiry Notification\n\n'
                                f'Employee: {employee.name}\n'
                                f'Manager: {manager.name}\n'
                                f'Certification: {certificate_name}\n'
                                f'Expiry Date: {expiry_date.strftime("%B %d, %Y")}\n'
                                f'Days Remaining: {days_until_expiry} days\n'
                                f'Notification Sent: {today.strftime("%B %d, %Y")}\n\n'
                                f'Click this activity to view all certificates for this employee.',
                        'res_model_id': self.env['ir.model']._get_id('certificate.notification.record'),
                        'res_id': notification_record.id,
                        'user_id': manager.user_id.id,
                        'date_deadline': expiry_date
                    })
                    logger.info(f"Created activity for {certificate_name} - {employee.name}")
                except Exception as e:
                    logger.error(f"Error creating activity for {certificate_name}: {e}")
                    continue

        return True


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def action_view_certificates(self):
        """Action to view certificates for this employee"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Certificates - {self.name}',
            'res_model': 'hr.resume.line',
            'view_mode': 'list,form',
            'domain': [
                ('employee_id', '=', self.id),
                ('display_type', '=', 'certification')
            ],
            'context': {
                'default_employee_id': self.id,
                'default_display_type': 'certification'
            },
            'target': 'current',
        }