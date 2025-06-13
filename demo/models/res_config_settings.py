from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    employee_prefix_default = fields.Char(
        string='Default Employee ID Prefix',
        config_parameter='employee_id_format.default_prefix',
        help='Default prefix for new employee IDs. The number part will be the employee database ID.'
    )

    employee_suffix_default = fields.Char(
        string='Default Employee ID Suffix',
        config_parameter='employee_id_format.default_suffix',
        help='Default suffix for new employee IDs (optional).'
    )

    employee_number_format = fields.Selection([
        ('{:03d}', '3 digits (001, 002, 003)'),
        ('{:04d}', '4 digits (0001, 0002, 0003)'),
        ('{:05d}', '5 digits (00001, 00002, 00003)'),
        ('{}', 'No leading zeros (1, 2, 3)'),
    ], string='Number Format',
        config_parameter='employee_id_format.number_format',
        help='Format for the numeric part of employee IDs (uses employee database ID)')

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('employee_id_format.default_prefix', self.employee_prefix_default or 'EMP')
        set_param('employee_id_format.default_suffix', self.employee_suffix_default or '')
        set_param('employee_id_format.number_format', self.employee_number_format or '{}')

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            employee_prefix_default=get_param('employee_id_format.default_prefix', default='EMP'),
            employee_suffix_default=get_param('employee_id_format.default_suffix', default=''),
            employee_number_format=get_param('employee_id_format.number_format', default='{}'),
        )
        return res