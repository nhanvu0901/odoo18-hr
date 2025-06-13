# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


# class EmployeeDynamicField(models.TransientModel):
#     _name = 'employee.dynamic.field'
#     _description = 'Dynamic Field Definition'
    
#     # Field creation options (from custom_hr module)
#     field_description = fields.Char(string='Field Label', required=True)
#     required = fields.Boolean(string='Required')
#     readonly = fields.Boolean(string='Readonly', default=False)
#     widget = fields.Selection([
#         ('image', 'Image'),
#         # ('many2many_tags', 'Tags'),
#         # ('binary', 'Binary'),
#         ('radio', 'Radio'),
#         ('priority', 'Priority'),
#         # ('monetary', 'Monetary'),
#         ('selection', 'Selection')
#     ], string='Widget')
#     selection_field = fields.Char(string="Selection Options")
#     field_type = fields.Selection(selection='get_possible_field_types', string='Field Type', required=True)
#     dynamic_tab_id = fields.Many2one('employee.dynamic.tabs', string='Dynamic Tab')
    
#     @api.model
#     def get_possible_field_types(self):
#         """Return all available field types other than 'one2many' and 'reference' fields."""
#         field_list = sorted((key, key) for key in fields.MetaField.by_type)
#         field_list.remove(('one2many', 'one2many'))
#         field_list.remove(('reference', 'reference'))
#         field_list.remove(('many2one', 'many2one'))
#         field_list.remove(('many2many', 'many2many'))
#         field_list.remove(('many2one_reference', 'many2one_reference'))
#         field_list.remove(('monetary', 'monetary'))
#         field_list.remove(('properties', 'properties'))
#         field_list.remove(('properties_definition', 'properties_definition'))
#         return field_list
        
#     @api.onchange('field_type')
#     def onchange_field_type(self):
#         """Clear widget when field type changes"""
#         if self.field_type:
#             self.widget = False
            
#     def format_selection_field(self, selection_text):
#         """Format comma-separated values into proper selection field format
        
#         Takes a string like 'blue, yellow, red' and returns
#         "[('blue', 'Blue'), ('yellow', 'Yellow'), ('red', 'Red')]"
#         """
#         if not selection_text:
#             return "[]"
            
#         # Split by comma and strip whitespace
#         values = [value.strip() for value in selection_text.split(',') if value.strip()]
        
#         # Format each value as ('lowercase_value', 'Capitalized_Value')
#         formatted_values = []
#         for value in values:
#             key = value.lower()
#             label = value.capitalize()
#             formatted_values.append(f"('{key}', '{label}')")
            
#         # Combine into selection field format
#         if formatted_values:
#             return "[" + ", ".join(formatted_values) + "]"
#         return "[]"


# class EmployeeDynamicTabs(models.TransientModel):
#     _name = 'employee.dynamic.tabs'
#     _description = 'Dynamic Tabs'

#     # Tab definition fields
#     tab_description = fields.Char(string='Tab Label', required=True)
    
#     # One2many relationship to field definitions
#     field_ids = fields.One2many('employee.dynamic.field', 'dynamic_tab_id', string='Custom Fields')
#     model_id = fields.Many2one('ir.model', string='Model', required=False,
#                               default=lambda self: self.env.ref('hr.model_hr_employee').id,
#                               readonly=True)
                              
#     # We don't need these methods here anymore, they are moved to EmployeeDynamicField

#     def create_tab(self):
#         """
#         Prepares data from the wizard and creates an hr.custom.tab record.
#         The HrCustomTab model will then handle the actual tab and field creation in the UI.
#         """
#         self.ensure_one()

#         custom_field_values_list = []
#         for field_def in self.field_ids: # field_ids are employee.dynamic.field records
#             custom_field_values = {
#                 'field_description': field_def.field_description,
#                 'field_type': field_def.field_type,
#                 'selection_field': field_def.selection_field, # Stored as raw string, HrCustomField will format if needed
#                 'widget': field_def.widget,
#                 'required': field_def.required,
#                 'readonly': field_def.readonly,
#             }
#             custom_field_values_list.append((0, 0, custom_field_values))

#         # Create the main hr.custom.tab record, linking the custom field definitions.
#         # The HrCustomTab.create method (which calls its own create_tab) will handle view and ir.model.fields creation.
#         self.env['hr.custom.tab'].sudo().create({
#             'tab_label': self.tab_description,
#             'field_ids': custom_field_values_list, # This creates hr.custom.field records
#         })

#         # Caches will be cleared by HrCustomTab's create_tab method after view/field manipulation.
#         # self.env['ir.ui.view'].clear_caches()
#         # self.env['ir.model.fields'].clear_caches()

#         return {
#             'type': 'ir.actions.client',
#             'tag': 'reload',
#         }


class HrCustomField(models.Model):
    _name = 'hr.custom.field'
    _description = 'Custom HR Field Definition'
    
    # Field creation options
    field_description = fields.Char(string='Field Label', required=True)
    required = fields.Boolean(string='Required')
    readonly = fields.Boolean(string='Readonly', default=False)
    widget = fields.Selection([
        ('image', 'Image'),
        # ('many2many_tags', 'Tags'),
        # ('binary', 'Binary'),
        ('radio', 'Radio'),
        ('priority', 'Priority'),
        # ('monetary', 'Monetary'),
        ('selection', 'Selection')
    ], string='Widget')
    selection_field = fields.Char(string="Selection Options")
    field_type = fields.Selection(selection='get_possible_field_types', string='Field Type', required=True)
    custom_tab_id = fields.Many2one('hr.custom.tab', string='Custom Tab')
    
    @api.model
    def get_possible_field_types(self):
        """Return all available field types other than 'one2many' and 'reference' fields."""
        field_list = sorted((key, key) for key in fields.MetaField.by_type)
        field_list.remove(('one2many', 'one2many'))
        field_list.remove(('reference', 'reference'))
        field_list.remove(('many2one', 'many2one'))
        field_list.remove(('many2many', 'many2many'))
        field_list.remove(('many2one_reference', 'many2one_reference'))
        field_list.remove(('monetary', 'monetary'))
        field_list.remove(('properties', 'properties'))
        field_list.remove(('properties_definition', 'properties_definition'))
        return field_list
        
    @api.onchange('field_type')
    def onchange_field_type(self):
        """Clear widget when field type changes"""
        if self.field_type:
            self.widget = False
            
    def format_selection_field(self, selection_text):
        """Format comma-separated values into proper selection field format
        
        Takes a string like 'blue, yellow, red' and returns
        "[('blue', 'Blue'), ('yellow', 'Yellow'), ('red', 'Red')]"
        """
        if not selection_text:
            return "[]"
            
        # Split by comma and strip whitespace
        values = [value.strip() for value in selection_text.split(',') if value.strip()]
        
        # Format each value as ('lowercase_value', 'Capitalized_Value')
        formatted_values = []
        for value in values:
            key = value.lower()
            label = value.capitalize()
            formatted_values.append(f"('{key}', '{label}')")
            
        # Combine into selection field format
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
        """Convert tab_label to a valid technical name"""
        if not tab_label:
            return ''
            
        # Convert to lowercase and replace spaces with underscores
        page_name = tab_label.lower().replace(' ', '_')
        # Remove any non-alphanumeric characters except underscores
        page_name = ''.join(c for c in page_name if c.isalnum() or c == '_')
        # Add x_ prefix if needed
        if not page_name.startswith('x_'):
            page_name = 'x_' + page_name
        return page_name
    
    def unlink(self):
        """Override unlink to remove the view inheritance when a tab is deleted."""
        views_to_delete_list = self.env['ir.ui.view']
        for tab in self:
            view_technical_name = tab._get_view_technical_name()
            # Search for the view by its stable technical name
            view_to_delete = self.env['ir.ui.view'].sudo().search([
                ('name', '=', view_technical_name),
                ('model', '=', 'hr.employee'), # Ensure it's for the correct model
            ], limit=1)
            if view_to_delete:
                views_to_delete_list |= view_to_delete

        res = super(HrCustomTab, self).unlink()

        if res and views_to_delete_list:
            views_to_delete_list.sudo().unlink()
            self.env['ir.ui.view'].clear_caches()

        return True

    def action_remove_from_employee_form(self):
        """
        Action method to remove the selected custom tabs from the employee form.
        This performs the unlink operation for the selected records and then reloads the UI.
        """
        if not self:
            return True  # No records selected, do nothing or return appropriate response

        # Call the existing unlink method for the selected records
        self.unlink()

        # Return an action to reload the client interface
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'target': 'main',  # Ensures a full reload of the main content area
        }

    
    @api.model
    def create(self, vals):
        """Override create to automatically render the tab in the employee form."""
        record = super(HrCustomTab, self).create(vals)
        record.create_tab() 
        return record

    def write(self, vals):
        """Override write to re-render the tab in the employee form if necessary."""
        res = super(HrCustomTab, self).write(vals)
        for tab in self:
            tab.create_tab()
        return res
        
    def _get_view_technical_name(self):
        """Generates a stable technical name for the ir.ui.view record.
           This name is used to find and update the view specific to this hr.custom.tab record.
        """
        self.ensure_one()
        return f"custom_tab_hr.dynamic_hr_employee_tab_{self.id}"

    def create_tab(self):
        """Ensures the custom tab's view exists and is correctly configured in the employee form.
           This method is idempotent: it creates the view if it doesn't exist, or updates it if it does.
        """
        self.ensure_one()

        # page_name is used for the 'name' attribute of the <page> tag in XML arch_base
        page_name = self._get_formatted_name(self.tab_label)
        
        # Get the base employee form view
        inherit_id = self.env.ref('hr.view_employee_form')
        
        # Initialize the XML architecture for the view inheritance
        fields_xml = []
        
        # Process each field in the tab
        for field in self.field_ids:
            # Generate field name
            field_name = field.field_description.lower().replace(' ', '_')
            field_name = ''.join(c for c in field_name if c.isalnum() or c == '_')
            # Add x_ prefix if needed
            if not field_name.startswith('x_'):
                field_name = 'x_' + field_name
            
            # Create field properties based on field_type
            field_props = {
                'name': field_name,
                'string': field.field_description,
                'required': field.required,
                'readonly': field.readonly,
            }
            
            # Add field type specific attributes
            if field.field_type == 'selection' and field.selection_field:
                field_props['selection'] = field.format_selection_field(field.selection_field)
            
            # Add widget if specified
            if field.widget:
                field_props['widget'] = field.widget
            
            # Create the field in the model
            try:
                # Check if field already exists
                existing_field = self.env['ir.model.fields'].sudo().search([
                    ('name', '=', field_name),
                    ('model', '=', 'hr.employee')
                ])
                
                if not existing_field:
                    # Create field if it doesn't exist
                    self.env['ir.model.fields'].sudo().create({
                        'name': field_name,
                        'field_description': field.field_description,
                        'model': 'hr.employee',
                        'model_id': self.env.ref('hr.model_hr_employee').id,
                        'ttype': field.field_type,
                        'required': field.required,
                        'readonly': field.readonly,
                        'selection': field_props.get('selection', False),
                    })
                
                # Add to XML architecture
                attrs = {}
                if field.required:
                    attrs['required'] = "1"
                if field.readonly:
                    attrs['readonly'] = "1"
                if field.widget:
                    attrs['widget'] = field.widget
                
                # Format attrs as string if needed
                attrs_str = ''
                if attrs:
                    attrs_str = ' ' + ' '.join(f'{k}="{v}"' for k, v in attrs.items())
                
                # Add field to XML
                fields_xml.append(f'<field name="{field_name}"{attrs_str}/>')
                
            except Exception as e:
                # Log error and continue with next field
                import logging
                _logger = logging.getLogger(__name__)
                _logger.error("Error creating custom field %s: %s", field_name, e)
        
        # Combine all field XML
        all_fields_xml = '\n                                          '.join(fields_xml)
        
        # Prepare the tab XML with the fields if needed
        if fields_xml:
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
            # Define a stable technical name for the ir.ui.view record
            view_technical_name = self._get_view_technical_name()

            # Search for an existing view associated with this hr.custom.tab record
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
                view_values['name'] = view_technical_name # Set the stable name only on creation
                self.env['ir.ui.view'].sudo().create(view_values)
            
            # Properly invalidate view and model field caches in Odoo
            self.env['ir.ui.view'].clear_caches()
            self.env['ir.model.fields'].clear_caches()
            
            # When called from create/write, the ORM's return value (True/recordset) is used.
            # No specific client action is needed here for automatic updates.
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        except Exception as e:
            # Safer exception handling
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error("Error creating custom tab: %s", e)
            raise UserError("Error creating custom tab: %s" % e)
