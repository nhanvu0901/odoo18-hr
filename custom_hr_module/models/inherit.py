import logging

_logger = logging.getLogger(__name__)

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re





class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_id = fields.Char(
        string='Employee ID',
        help='Automatically generated Employee Identification Number based on prefix, employee database ID, and suffix',
        compute='_compute_employee_id',
        store=False,
        search='_search_employee_id'
    )
    employee_id_prefix = fields.Char(
        string='ID Prefix',
        size=10,
        help='Prefix for the employee ID (e.g., EMP, DEV, HR)',
    )
    employee_id_suffix = fields.Char(
        string='ID Suffix',
        size=10,
        help='Suffix for the employee ID (e.g., HR, DEV, TMP)',
    )
    employee_id_public = fields.Char()

    @api.depends('employee_id_prefix', 'employee_id_suffix')
    def _compute_employee_id(self):
        for record in self:
            record_id = None

            if hasattr(record.id, 'origin') and record.id.origin:
                record_id = record.id.origin
            elif isinstance(record.id, int) and record.id > 0:
                record_id = record.id
            elif hasattr(record, '_origin') and record._origin.id:
                record_id = record._origin.id

            if record_id:
                prefix = record.employee_id_prefix or self._get_default_prefix()
                prefix = re.sub(r'[^A-Za-z0-9_]', '', prefix).upper()

                suffix = record.employee_id_suffix or self._get_default_suffix()
                suffix = re.sub(r'[^A-Za-z0-9_]', '', suffix).upper()

                number_format = self._get_number_format()
                try:
                    if number_format == '{}':
                        formatted_number = str(record_id)
                    else:
                        formatted_number = number_format.format(record_id)

                    employee_id_parts = [prefix, formatted_number]
                    if suffix:
                        employee_id_parts.append(suffix)

                    record.employee_id = "-".join(employee_id_parts)
                except (ValueError, TypeError) as e:
                    _logger.error(
                        "Error formatting employee ID number %s with format '%s': %s. Using default format.",
                        record_id, number_format, str(e)
                    )

                    formatted_number = "{:03d}".format(record_id)
                    employee_id_parts = [prefix, formatted_number]
                    if suffix:
                        employee_id_parts.append(suffix)

                    record.employee_id = "-".join(employee_id_parts)
            else:
                prefix = record.employee_id_prefix or self._get_default_prefix()
                prefix = re.sub(r'[^A-Za-z0-9_]', '', prefix).upper()

                suffix = record.employee_id_suffix or self._get_default_suffix()
                suffix = re.sub(r'[^A-Za-z0-9_]', '', suffix).upper()

                employee_id_parts = [prefix, "---"]
                if suffix:
                    employee_id_parts.append(suffix)

                record.employee_id = "-".join(employee_id_parts)

    def _search_employee_id(self, operator, value):
        if operator in ('=', '!=', 'like', 'ilike', 'in', 'not in'):
            all_employees = self.search([])
            matching_ids = []

            for employee in all_employees:
                computed_id = employee.employee_id
                if operator == '=' and computed_id == value:
                    matching_ids.append(employee.id)
                elif operator == '!=' and computed_id != value:
                    matching_ids.append(employee.id)
                elif operator in ('like', 'ilike'):
                    if value.lower() in computed_id.lower():
                        matching_ids.append(employee.id)
                elif operator == 'in' and computed_id in value:
                    matching_ids.append(employee.id)
                elif operator == 'not in' and computed_id not in value:
                    matching_ids.append(employee.id)

            return [('id', 'in', matching_ids)]

        return [('id', '=', -1)]  # Return empty result for unsupported operators

    def _get_default_prefix(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'employee_id_format.default_prefix', 'EMP'
        )

    def _get_default_suffix(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'employee_id_format.default_suffix', ''
        )

    def _get_number_format(self):
        valid_formats = ['{:03d}', '{:04d}', '{:05d}', '{}']

        number_format = self.env['ir.config_parameter'].sudo().get_param(
            'employee_id_format.number_format', '{:03d}'
        )

        if number_format not in valid_formats:
            _logger.warning(
                "Invalid number format '%s' found in config. Using default '{:03d}'",
                number_format
            )
            number_format = '{:03d}'

        return number_format

    @api.constrains('employee_id_prefix', 'employee_id_suffix')
    def _check_prefix_suffix_format(self):
        for record in self:
            if record.employee_id_prefix:
                if not re.match(r'^[A-Za-z0-9_]+$', record.employee_id_prefix):
                    raise ValidationError(
                        _("Prefix can only contain letters, numbers, and underscores")
                    )
                if len(record.employee_id_prefix) > 10:
                    raise ValidationError(
                        _("Prefix cannot be longer than 10 characters")
                    )

            if record.employee_id_suffix:
                if not re.match(r'^[A-Za-z0-9_]+$', record.employee_id_suffix):
                    raise ValidationError(
                        _("Suffix can only contain letters, numbers, and underscores")
                    )
                if len(record.employee_id_suffix) > 10:
                    raise ValidationError(
                        _("Suffix cannot be longer than 10 characters")
                    )


class HrEmployeePublicInherit(models.Model):
    _inherit = 'hr.employee.public'

    employee_id_public = fields.Char(
        string='Custom Employee ID',
        help='Displays the computed Employee ID from the hr.employee model',
        compute='_compute_employee_id_public_field',
        store=False,
    )

    def _compute_employee_id_public_field(self):

        for record in self:
            try:
                employee = self.env['hr.employee'].sudo().browse(record.id)
                if employee.exists() and employee.employee_id:
                    record.employee_id_public = employee.employee_id
                else:
                    record.employee_id_public = False
            except Exception as e:
                _logger.error(
                    "Error computing 'employee_id_public' field for public record %s: %s",
                    record.id, str(e)
                )
                record.employee_id_public = False


class InheritIrModelFields(models.Model):
    _inherit = 'ir.ui.view'

    is_dynamic_tab = fields.Boolean(default=False,
                                    help='Indicates if this view was created by the custom_tab_hr module')