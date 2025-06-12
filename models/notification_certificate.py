from datetime import datetime, timedelta
from odoo import api, fields, models
import logging

logger = logging.getLogger(__name__)


class CertificateNotificationRecord(models.Model):
    """Custom model to handle certificate notifications with consistent redirect behavior"""
    _name = 'certificate.notification.record'
    _description = 'Certificate Notification Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    display_name = fields.Char('Name', compute='_compute_display_name', store=True)
    name = fields.Char('Name', compute='_compute_display_name', store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    certificate_id = fields.Many2one('hr.resume.line', string='Certificate',
                                     ondelete='set null')  # Changed to set null instead of cascade
    expiry_date = fields.Date('Expiry Date')
    days_remaining = fields.Integer('Days Remaining', compute='_compute_days_remaining', store=True)

    # Additional fields to store certificate info in case the original record is deleted
    certificate_name = fields.Char('Certificate Name', help='Backup name in case certificate record is deleted')
    certificate_description = fields.Text('Certificate Description', help='Backup description')

    @api.depends('employee_id', 'certificate_id', 'certificate_name')
    def _compute_display_name(self):
        for record in self:
            try:
                if record.employee_id:
                    employee_name = record.employee_id.name or "Unknown Employee"

                    # Try to get certificate name from the linked record first
                    certificate_name = None
                    if record.certificate_id:
                        try:
                            # Test if the certificate record exists and is accessible
                            if hasattr(record.certificate_id, 'exists') and record.certificate_id.exists():
                                certificate_name = (
                                        getattr(record.certificate_id, 'name', None) or
                                        getattr(record.certificate_id, 'display_name', None) or
                                        getattr(record.certificate_id, 'description', None)
                                )
                            else:
                                # Certificate record doesn't exist, clear the reference
                                logger.info(
                                    f"Certificate record doesn't exist for notification {record.id}, clearing reference")
                                record._clear_broken_certificate_reference()
                                certificate_name = None
                        except Exception as e:
                            logger.warning(f"Error accessing certificate_id for record {record.id}: {e}")
                            # Clear broken reference
                            record._clear_broken_certificate_reference()
                            certificate_name = None

                    # Fallback to stored certificate name
                    if not certificate_name:
                        certificate_name = record.certificate_name or f"Certificate (Deleted)"

                    computed_name = f"{employee_name} - {certificate_name}"
                    record.display_name = computed_name
                    record.name = computed_name
                else:
                    record.display_name = "Certificate Notification"
                    record.name = "Certificate Notification"
            except Exception as e:
                logger.warning(f"Error computing display_name for record {record.id}: {e}")
                record.display_name = "Certificate Notification"
                record.name = "Certificate Notification"

    def _clear_broken_certificate_reference(self):
        """Safely clear broken certificate reference"""
        try:
            self.env.cr.execute("""
                UPDATE certificate_notification_record 
                SET certificate_id = NULL 
                WHERE id = %s
            """, (self.id,))
            self.env.cr.commit()
        except Exception as e:
            logger.error(f"Failed to clear broken reference for record {self.id}: {e}")
            self.env.cr.rollback()

    def web_read(self, specification):
        """Override web_read to handle broken references in web interface"""
        # Clean broken references before web read
        self._cleanup_broken_references()
        try:
            return super().web_read(specification)
        except (AttributeError, TypeError) as e:
            if "'_unknown' object has no attribute" in str(e):
                logger.warning(f"Broken reference in web_read: {e}")
                # Clean again and retry
                self._cleanup_broken_references()
                self.env.invalidate_all()
                try:
                    return super().web_read(specification)
                except Exception:
                    # Return safe minimal data
                    return []

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Override search_read to handle broken references in searches"""
        try:
            # First do a normal search to get the IDs
            ids = self.search(domain or [], offset=offset, limit=limit, order=order)
            # Clean any broken references in the found records
            if ids:
                ids._cleanup_broken_references()
            # Then read the cleaned records
            return ids.read(fields)
        except Exception as e:
            logger.error(f"Error in search_read: {e}")
            # Fallback to minimal search without problematic records
            try:
                # Search for records that definitely don't have broken references
                safe_domain = (domain or []) + [
                    '|',
                    ('certificate_id', '=', False),
                    ('certificate_id', 'in', self.env['hr.resume.line'].search([]).ids)
                ]
                return super().search_read(safe_domain, fields, offset, limit, order)
            except Exception:
                return []

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
        self.ensure_one()
        if not self.employee_id:
            return {'type': 'ir.actions.act_window_close'}

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

    @api.model
    def create(self, vals):
        """Override create to store certificate info as backup"""
        record = super().create(vals)
        # Store certificate name as backup in case the certificate record gets deleted
        if record.certificate_id:
            try:
                if record.certificate_id.exists():
                    certificate_name = (
                            getattr(record.certificate_id, 'name', None) or
                            getattr(record.certificate_id, 'display_name', None) or
                            getattr(record.certificate_id, 'description', None) or
                            f"Certificate {record.certificate_id.id}"
                    )
                    record.certificate_name = certificate_name
                    record.certificate_description = getattr(record.certificate_id, 'description', '')
            except Exception as e:
                logger.warning(f"Error storing certificate backup info: {e}")
        return record

    def read(self, fields=None, load='_classic_read'):
        """Override read to handle broken certificate references more robustly"""
        # First, try to clean any broken references in this recordset
        self._cleanup_broken_references()

        try:
            return super().read(fields, load)
        except (AttributeError, TypeError) as e:
            if "'_unknown' object has no attribute" in str(e):
                logger.warning(f"Broken certificate reference detected in notification records: {e}")

                # Force cleanup and try again
                self._cleanup_broken_references()

                try:
                    # Clear cache and try reading again
                    self.env.invalidate_all()
                    return super().read(fields, load)
                except Exception as retry_error:
                    logger.error(f"Failed to read after cleanup: {retry_error}")
                    # Return minimal safe data as fallback
                    if fields:
                        return [{field: False if field != 'id' else rec_id for field in fields}
                                for rec_id in self.ids]
                    else:
                        return [{'id': rec_id, 'display_name': 'Broken Notification Record'}
                                for rec_id in self.ids]
            raise

    def _cleanup_broken_references(self):
        """Helper method to clean broken references for this recordset"""
        if not self.ids:
            return

        try:
            # Use SQL to directly fix broken references without triggering ORM issues
            self.env.cr.execute("""
                UPDATE certificate_notification_record 
                SET certificate_id = NULL 
                WHERE id IN %s 
                AND certificate_id IS NOT NULL 
                AND certificate_id NOT IN (
                    SELECT id FROM hr_resume_line WHERE id IS NOT NULL
                )
            """, (tuple(self.ids),))

            if self.env.cr.rowcount > 0:
                logger.info(f"Cleared {self.env.cr.rowcount} broken certificate references")
                self.env.cr.commit()

        except Exception as sql_error:
            logger.error(f"Error during broken reference cleanup: {sql_error}")
            self.env.cr.rollback()

    @api.model
    def default_get(self, fields_list):
        """Override default_get to auto-redirect when opened from activity"""
        result = super().default_get(fields_list)
        # Check if we're being opened from an activity context
        if self.env.context.get('active_model') == 'mail.activity':
            # This will trigger the redirect behavior in the view
            result['auto_redirect'] = True
        return result

    def open_record(self):
        """Override the default open action to redirect to certificates"""
        return self.action_view_certificate()


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

            # Verify the record still exists
            if not record.exists():
                logger.warning("Skipping non-existent certificate record")
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
                        'expiry_date': expiry_date,
                        'certificate_name': certificate_name,  # Store as backup
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
                        'note': f'🚨 Certification Expiry Notification\n\n'
                                f'Employee: {employee.name}\n'
                                f'Manager: {manager.name}\n'
                                f'Certification: {certificate_name}\n'
                                f'Expiry Date: {expiry_date.strftime("%B %d, %Y")}\n'
                                f'Days Remaining: {days_until_expiry} days\n'
                                f'Notification Sent: {today.strftime("%B %d, %Y")}\n\n'
                                f'📋 Click this activity to automatically view all certificates for this employee.\n'
                                f'💡 The notification will auto-redirect to the certificate list.',
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

    @api.model
    def cleanup_broken_notifications(self):
        """Utility method to clean up notification records with broken certificate references"""
        logger.info("Cleaning up broken certificate notification records...")

        # Use SQL to find and clean broken references more efficiently
        try:
            # Find notification records with certificate_id that don't exist in hr_resume_line
            self.env.cr.execute("""
                SELECT id FROM certificate_notification_record 
                WHERE certificate_id IS NOT NULL 
                AND certificate_id NOT IN (
                    SELECT id FROM hr_resume_line WHERE id IS NOT NULL
                )
            """)
            broken_ids = [row[0] for row in self.env.cr.fetchall()]

            if broken_ids:
                # Update broken references to NULL
                self.env.cr.execute("""
                    UPDATE certificate_notification_record 
                    SET certificate_id = NULL 
                    WHERE id IN %s
                """, (tuple(broken_ids),))

                logger.info(f"Fixed {len(broken_ids)} broken certificate references")

                # Also clean up any notification records without employees
                self.env.cr.execute("""
                    DELETE FROM certificate_notification_record 
                    WHERE employee_id IS NULL 
                    OR employee_id NOT IN (
                        SELECT id FROM hr_employee WHERE id IS NOT NULL
                    )
                """)

                deleted_count = self.env.cr.rowcount
                if deleted_count > 0:
                    logger.info(f"Deleted {deleted_count} notification records with missing employees")

                self.env.cr.commit()
                return len(broken_ids) + deleted_count
            else:
                logger.info("No broken notification records found")
                return 0

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            self.env.cr.rollback()
            return 0


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