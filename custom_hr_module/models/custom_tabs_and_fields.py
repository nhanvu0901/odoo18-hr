# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError

class HrCustomField(models.Model):
    _name = 'hr.custom.field'
    _description = 'Custom HR Field Definition'
    
    field_description = fields.Char(string='Field Label', required=True)
    required = fields.Boolean(string='Required')
    readonly = fields.Boolean(string='Readonly', default=False)
    widget = fields.Selection([
        ('image', 'Image'),
        # ('many2many_tags', 'Tags'),
        # ('binary', 'Binary'),
        ('radio', 'Radio'),
        # ('priority', 'Priority'),
        # ('monetary', 'Monetary'),
        ('selection', 'Selection')
    ], string='Widget')
    selection_field = fields.Char(string="Selection Options")
    field_type = fields.Selection(selection='get_possible_field_types', string='Field Type', required=True)
    custom_tab_id = fields.Many2one('hr.custom.tab', string='Custom Tab')
    
    @api.model
    def get_possible_field_types(self):
        field_list = sorted((key, key) for key in fields.MetaField.by_type)
        field_list.remove(('one2many', 'one2many'))
        field_list.remove(('reference', 'reference'))
        field_list.remove(('binary', 'binary'))
        field_list.remove(('many2one', 'many2one'))
        field_list.remove(('many2many', 'many2many'))
        field_list.remove(('many2one_reference', 'many2one_reference'))
        field_list.remove(('monetary', 'monetary'))
        field_list.remove(('properties', 'properties'))
        field_list.remove(('properties_definition', 'properties_definition'))
        return field_list
        
    @api.onchange('field_type')
    def onchange_field_type(self):
        if self.field_type:
            self.widget = False
            
    def format_selection_field(self, selection_text):
        if not selection_text:
            return "[]"
            
        values = [value.strip() for value in selection_text.split(',') if value.strip()]
        
        formatted_values = []
        for value in values:
            formatted_values.append(f"('{value}', '{value}')")
            
        if formatted_values:
            return "[" + ", ".join(formatted_values) + "]"
        return "[]"

class HrCustomTab(models.Model):
    _name = 'hr.custom.tab'
    _description = 'Custom HR Tabs'
    _order = 'id'
    
    tab_label = fields.Char(string='Tab Label', required=True)
    field_ids = fields.One2many('hr.custom.field', 'custom_tab_id', string='Custom Fields')

    
    def _get_formatted_name(self, tab_label):
        if not tab_label:
            return ''
            
        page_name = tab_label.lower().replace(' ', '_')
        page_name = ''.join(c for c in page_name if c.isalnum() or c == '_')
        if not page_name.startswith('x_'):
            page_name = 'x_' + page_name
        return page_name
    
    def unlink(self):
        views_to_delete_list = self.env['ir.ui.view']
        fields_to_delete = self.env['ir.model.fields']
        
        for tab in self:
            view_technical_name = tab._get_view_technical_name()
            view_to_delete = self.env['ir.ui.view'].sudo().search([
                ('name', '=', view_technical_name),
                ('model', '=', 'hr.employee'),
            ], limit=1)
            
            if view_to_delete:
                views_to_delete_list |= view_to_delete
            
            for field in tab.field_ids:
                field_name = field.field_description.lower().replace(' ', '_')
                field_name = ''.join(c for c in field_name if c.isalnum() or c == '_')
                if not field_name.startswith('x_'):
                    field_name = 'x_' + field_name
                
                model_field = self.env['ir.model.fields'].sudo().search([
                    ('model', '=', 'hr.employee'),
                    ('name', '=', field_name)
                ], limit=1)
                
                if model_field:
                    fields_to_delete |= model_field
        
        if views_to_delete_list:
            self.env['ir.ui.view'].clear_caches()
            views_to_delete_list.sudo().unlink()
            self.env['ir.ui.view'].clear_caches()
        
        res = super(HrCustomTab, self).unlink()
        if res and fields_to_delete:
            try:
                fields_to_delete.sudo().unlink()
            except Exception as e:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.error("Error deleting fields: %s", e)

        return True

    def action_remove_from_employee_form(self):
        if not self:
            return True  

        self.unlink()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'target': 'main',
        }

    
    @api.model
    def create(self, vals):
        record = super(HrCustomTab, self).create(vals)
        record.create_tab() 
        return record

    def write(self, vals):
        res = super(HrCustomTab, self).write(vals)
        for tab in self:
            tab.create_tab()
        return res
        
    def _get_view_technical_name(self):
        self.ensure_one()
        return f"custom_tab_hr.dynamic_hr_employee_tab_{self.id}"

    def create_tab(self):
        self.ensure_one()

        page_name = self._get_formatted_name(self.tab_label)
        
        inherit_id = self.env.ref('hr.view_employee_form')
        
        fields_xml = []
        
        for field in self.field_ids:
            field_name = field.field_description.lower().replace(' ', '_')
            field_name = ''.join(c for c in field_name if c.isalnum() or c == '_')
            if not field_name.startswith('x_'):
                field_name = 'x_' + field_name
            
            field_props = {
                'name': field_name,
                'string': field.field_description,
                'required': field.required,
                'readonly': field.readonly,
            }
            
            if field.field_type == 'selection' and field.selection_field:
                field_props['selection'] = field.format_selection_field(field.selection_field)
            
            if field.widget:
                field_props['widget'] = field.widget
            
            try:
                existing_field = self.env['ir.model.fields'].sudo().search([
                    ('name', '=', field_name),
                    ('model', '=', 'hr.employee')
                ], limit=1)
                
                if not existing_field:
                    self.env['ir.model.fields'].sudo().create({
                        'name': field_name,
                        'field_description': field.field_description,
                        'model': 'hr.employee',
                        'model_id': self.env.ref('hr.model_hr_employee').id,
                        'ttype': field.field_type,
                        'required': field.required,
                        'readonly': field.readonly,
                        'selection': field_props.get('selection', False) if field.field_type == 'selection' else False,
                        'state': 'manual',
                    })
                
                attrs = {}
                if field.required:
                    attrs['required'] = "1"
                if field.readonly:
                    attrs['readonly'] = "1"
                if field.widget:
                    attrs['widget'] = field.widget
                
                attrs_str = ''
                if attrs:
                    attrs_str = ' ' + ' '.join(f'{k}="{v}"' for k, v in attrs.items())
                    
                if field.widget == 'image':
                    attrs_str += ' style="width: 90px; height: 90px; object-fit: contain;"'
                
                fields_xml.append(f'<field name="{field_name}"{attrs_str}/>')
                
            except Exception as e:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.error("Error creating custom field %s: %s", field_name, e)
        
        if fields_xml:
            odd_fields = [fields_xml[i] for i in range(len(fields_xml)) if i % 2 == 1]
            even_fields = [fields_xml[i] for i in range(len(fields_xml)) if i % 2 == 0]

            group_odd = '<group>%s</group>' % '\n'.join(odd_fields) if odd_fields else ''
            group_even = '<group>%s</group>' % '\n'.join(even_fields) if even_fields else ''

            all_fields_xml = '\n'.join([group_even, group_odd])

            arch_base = '''<?xml version="1.0"?>
                            <data>
                                <xpath expr="//notebook" position="inside">
                                    <page string="%s" name="%s">
                                        <group>
                                            %s
                                        </group>
                                    </page>
                                </xpath>
                            </data>''' % (self.tab_label, page_name, all_fields_xml)
        else:
            arch_base = '''<?xml version="1.0"?>
                            <data>
                                <xpath expr="//notebook" position="inside">
                                    <page string="%s" name="%s">
                                        <group>
                                        </group>
                                    </page>
                                </xpath>
                            </data>''' % (self.tab_label, page_name)
        
        try:
            view_technical_name = self._get_view_technical_name()

            existing_view = self.env['ir.ui.view'].sudo().search([
                ('name', '=', view_technical_name),
                ('model', '=', 'hr.employee'),
            ], limit=1)

            view_values = {
                'type': 'form',
                'model': 'hr.employee',
                'mode': 'extension',
                'inherit_id': self.env.ref('hr.view_employee_form').id,
                'arch_base': arch_base,
            }

            if existing_view:
                existing_view.sudo().write(view_values)
            else:
                view_values['name'] = view_technical_name
                self.env['ir.ui.view'].sudo().create(view_values)
            
            self.env['ir.ui.view'].clear_caches()
            self.env['hr.custom.field'].clear_caches()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error("Error creating custom tab: %s", e)
            raise UserError("Error creating custom tab: %s" % e)
