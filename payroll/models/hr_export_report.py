import io
import base64
from datetime import datetime
from dateutil import relativedelta
from odoo import fields, models, _
from odoo.exceptions import UserError
import xlsxwriter


class HrKKTNCNExport(models.TransientModel):
    _name = "hr.kk.tncn.export"
    _description = "Export KK-TNCN Report"

    month_from = fields.Selection(
        selection=[
            ('01', 'January'), ('02', 'February'), ('03', 'March'),
            ('04', 'April'), ('05', 'May'), ('06', 'June'),
            ('07', 'July'), ('08', 'August'), ('09', 'September'),
            ('10', 'October'), ('11', 'November'), ('12', 'December')
        ],
        string="From Month",
        required=True,
        default=lambda self: f"{datetime.now().month:02d}"
    )
    year_from = fields.Selection(
        selection="_get_year_selection",
        string="From Year",
        required=True,
        default=lambda self: str(datetime.now().year)
    )
    month_to = fields.Selection(
        selection=[
            ('01', 'January'), ('02', 'February'), ('03', 'March'),
            ('04', 'April'), ('05', 'May'), ('06', 'June'),
            ('07', 'July'), ('08', 'August'), ('09', 'September'),
            ('10', 'October'), ('11', 'November'), ('12', 'December')
        ],
        string="To Month",
        required=True,
        default=lambda self: f"{datetime.now().month:02d}"
    )
    year_to = fields.Selection(
        selection="_get_year_selection",
        string="To Year",
        required=True,
        default=lambda self: str(datetime.now().year)
    )

    export_file = fields.Binary(string="Export File", readonly=True)
    export_filename = fields.Char(string="Filename", readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft')

    def _get_year_selection(self):
        current_year = datetime.now().year
        years = []

        for year in range(current_year, current_year - 11, -1):
            years.append((str(year), str(year)))

        return years

    def _get_date_range(self):
        date_from = datetime.strptime(f"{self.year_from}-{self.month_from}-01", "%Y-%m-%d").date()

        date_to_temp = datetime.strptime(f"{self.year_to}-{self.month_to}-01", "%Y-%m-%d").date()
        date_to = (date_to_temp + relativedelta.relativedelta(months=1, days=-1))

        return date_from, date_to

    def _get_tax_deduction_amount(self, employee):
        base_deduction = 11000000
        dependent_children = employee.children or 0
        children_deduction = dependent_children * 4400000
        return int(base_deduction + children_deduction)

    def _calculate_personal_income_tax(self, taxable_income):
        if taxable_income <= 0:
            return 0

        if taxable_income <= 5000000:
            return round(taxable_income * 0.05)
        elif taxable_income <= 10000000:
            return round(taxable_income * 0.10 - 250000)
        elif taxable_income <= 18000000:
            return round(taxable_income * 0.15 - 750000)
        elif taxable_income <= 32000000:
            return round(taxable_income * 0.20 - 1650000)
        elif taxable_income <= 52000000:
            return round(taxable_income * 0.25 - 3250000)
        elif taxable_income <= 80000000:
            return round(taxable_income * 0.30 - 5850000)
        else:
            return round(taxable_income * 0.35 - 9850000)

    def _calculate_gross_by_category(self, payslip):
        gross_amount = 0

        for line in payslip.line_ids:
            if line.category_id and line.category_id.code in ['BASIC', 'ALW']:
                gross_amount += line.total

        if gross_amount == 0:
            gross_line = payslip.line_ids.filtered(lambda l: l.code == 'GROSS')
            if gross_line:
                gross_amount = gross_line[0].total

        return int(gross_amount)

    def _calculate_deductions_by_category(self, payslip):
        deduction_amount = 0

        for line in payslip.line_ids:
            if line.category_id and line.category_id.code == 'DED':
                deduction_amount += abs(line.total)

        return int(deduction_amount)

    def _calculate_pit_by_category(self, payslip):
        pit_amount = 0

        for line in payslip.line_ids:
            if line.category_id and line.category_id.code == 'DED':
                if line.code in ['PT', 'PIT', 'INCOME_TAX', 'TAX']:
                    pit_amount += abs(line.total)

        return int(pit_amount)

    def _get_payslip_data(self):
        date_from, date_to = self._get_date_range()

        period_start = date_from
        period_end = date_to

        payslips = self.env['hr.payslip'].search([
            ('state', '=', 'done'),
            ('date_from', '>=', period_start),
            ('date_to', '<=', period_end),
        ])

        if not payslips:
            raise UserError(_("No completed payslips found for the selected period."))

        employee_data = {}

        for payslip in payslips:
            employee = payslip.employee_id
            if employee.id not in employee_data:
                employee_data[employee.id] = {
                    'employee': employee,
                    'payslips': [],
                    'total_gross': 0,
                    'total_deduction': 0,
                    'total_payroll_deductions': 0,
                    'total_assessable': 0,
                    'total_pit': 0,
                    'month_work': 0
                }

            employee_data[employee.id]['month_work'] += 1
            employee_data[employee.id]['payslips'].append(payslip)

            gross_amount = self._calculate_gross_by_category(payslip)
            employee_data[employee.id]['total_gross'] += gross_amount

            pit_amount = self._calculate_pit_by_category(payslip)
            employee_data[employee.id]['total_pit'] += pit_amount

            payroll_deductions = self._calculate_deductions_by_category(payslip)
            if 'total_payroll_deductions' not in employee_data[employee.id]:
                employee_data[employee.id]['total_payroll_deductions'] = 0
            employee_data[employee.id]['total_payroll_deductions'] += payroll_deductions

        for emp_id, data in employee_data.items():
            employee = data['employee']

            monthly_deduction = self._get_tax_deduction_amount(employee)
            months_in_period = data['month_work']

            data['total_deduction'] = int(monthly_deduction * months_in_period)
            data['total_assessable'] = int(data['total_gross'] - data['total_deduction'])

            if data['total_assessable'] < 0:
                data['total_assessable'] = 0

            calculated_pit = self._calculate_personal_income_tax(data['total_assessable'])
            data['total_pit'] = int(calculated_pit)

            # Ensure all accumulated values are integers
            data['total_gross'] = int(data['total_gross'])
            data['total_payroll_deductions'] = int(data['total_payroll_deductions'])

        return employee_data

    def _create_excel_file(self, employee_data):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('KK-TNCN Report')

        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#D7E4BC'
        })

        data_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })

        number_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'num_format': '#,##0'
        })

        worksheet.set_column('A:A', 8)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 20)
        worksheet.set_column('E:E', 18)
        worksheet.set_column('F:F', 20)
        worksheet.set_column('G:G', 25)

        headers = [
            'No.',
            'Full Name',
            'Personal Tax ID',
            'Total taxable income (VND)',
            'Deduction (VND)',
            'Assessable income (VND)',
            'PIT (Personal Income Tax) payable (VND)'
        ]

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        row = 1
        for emp_id, data in employee_data.items():
            employee = data['employee']

            worksheet.write(row, 0, row, data_format)
            worksheet.write(row, 1, employee.name or '', data_format)
            worksheet.write(row, 2, '', data_format)
            worksheet.write(row, 3, int(data['total_gross']), number_format)
            worksheet.write(row, 4, int(data['total_deduction']), number_format)
            worksheet.write(row, 5, int(data['total_assessable']), number_format)
            worksheet.write(row, 6, int(abs(data['total_pit'])), number_format)

            row += 1

        workbook.close()
        output.seek(0)

        return output.getvalue()

    def export_kk_tncn(self):
        try:
            employee_data = self._get_payslip_data()

            if not employee_data:
                raise UserError(_("No payslip data found for the selected period."))

            excel_data = self._create_excel_file(employee_data)

            filename = f"KK-TNCN_{self.year_from}{self.month_from}_{self.year_to}{self.month_to}.xlsx"

            self.write({
                'export_file': base64.b64encode(excel_data),
                'export_filename': filename,
                'state': 'done'
            })

            return self.download_file()
        except Exception as e:
            raise UserError(_("Error generating KK-TNCN report: %s") % str(e))

    def download_file(self):
        if not self.export_file:
            raise UserError(_("No file available for download."))

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=hr.kk.tncn.export&id={self.id}&field=export_file&download=true&filename={self.export_filename}',
            'target': 'self',
        }


class HrQTTTNCNExport(models.TransientModel):
    _name = "hr.qtt.tncn.export"
    _description = "Export QTT-TNCN Report"

    year = fields.Selection(
        selection="_get_year_selection",
        string="Year",
        required=True,
        default=lambda self: str(datetime.now().year)
    )

    export_file = fields.Binary(string="Export File", readonly=True)
    export_filename = fields.Char(string="Filename", readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft')

    def _get_year_selection(self):
        current_year = datetime.now().year
        years = []

        for year in range(current_year, current_year - 11, -1):
            years.append((str(year), str(year)))

        return years

    def _calculate_personal_income_tax(self, taxable_income):
        if taxable_income <= 0:
            return 0

        if taxable_income <= 5000000:
            return round(taxable_income * 0.05)
        elif taxable_income <= 10000000:
            return round(taxable_income * 0.10 - 250000)
        elif taxable_income <= 18000000:
            return round(taxable_income * 0.15 - 750000)
        elif taxable_income <= 32000000:
            return round(taxable_income * 0.20 - 1650000)
        elif taxable_income <= 52000000:
            return round(taxable_income * 0.25 - 3250000)
        elif taxable_income <= 80000000:
            return round(taxable_income * 0.30 - 5850000)
        else:
            return round(taxable_income * 0.35 - 9850000)

    def _calculate_annual_personal_income_tax(self, taxable_income):
        if taxable_income <= 0:
            return 0

        taxable_millions = taxable_income / 1000000

        if taxable_millions <= 60:
            return round(taxable_income * 0.05 - 0)
        elif taxable_millions <= 120:
            return round(taxable_income * 0.10 - 3000000)
        elif taxable_millions <= 216:
            return round(taxable_income * 0.15 - 9000000)
        elif taxable_millions <= 384:
            return round(taxable_income * 0.20 - 21600000)
        elif taxable_millions <= 624:
            return round(taxable_income * 0.25 - 39600000)
        elif taxable_millions <= 960:
            return round(taxable_income * 0.30 - 64800000)
        else:
            return round(taxable_income * 0.35 - 96000000)

    def _get_gross_amount(self, payslip):
        gross_line = payslip.line_ids.filtered(lambda l: l.code == 'GROSS')
        return int(gross_line[0].total) if gross_line else 0

    def _get_deduction_amount(self, payslip):
        deduction_amount = 0
        for line in payslip.line_ids:
            if line.category_id and line.category_id.code == 'DED':
                deduction_amount += abs(line.total)
        return int(deduction_amount)

    def _get_taxable_income(self, payslip):
        taxable_lines = payslip.line_ids.filtered(lambda l: l.code in ['TAXABLE', 'TAXABLE_INCOME', 'TI'])
        if taxable_lines:
            return int(taxable_lines[0].total)

        gross_amount = self._get_gross_amount(payslip)
        deduction_amount = self._get_deduction_amount(payslip)
        return int(gross_amount - deduction_amount)

    def _calculate_gross_by_category(self, payslip):
        gross_amount = 0

        for line in payslip.line_ids:
            if line.category_id and line.category_id.code in ['BASIC', 'ALW']:
                gross_amount += line.total

        if gross_amount == 0:
            gross_line = payslip.line_ids.filtered(lambda l: l.code == 'GROSS')
            if gross_line:
                gross_amount = gross_line[0].total

        return int(gross_amount)

    def _calculate_pit_by_category(self, payslip):
        pit_amount = 0

        for line in payslip.line_ids:
            if line.category_id and line.category_id.code == 'DED':
                if line.code in ['PT', 'PIT', 'INCOME_TAX', 'TAX']:
                    pit_amount += abs(line.total)

        return int(pit_amount)

    def _calculate_deductions_by_category(self, payslip):
        deduction_amount = 0

        for line in payslip.line_ids:
            if line.category_id and line.category_id.code == 'DED':
                deduction_amount += abs(line.total)

        return int(deduction_amount)

    def _get_tax_deduction_amount(self, employee):
        base_deduction = 11000000
        dependent_children = employee.children or 0
        children_deduction = dependent_children * 4400000
        return int(base_deduction + children_deduction)

    def calculateKKTNCNEReport(self, payslips):
        if not payslips:
            raise UserError(_("No completed payslips found for the selected period."))

        employee_data = {}

        for payslip in payslips:
            employee = payslip.employee_id
            if employee.id not in employee_data:
                employee_data[employee.id] = {
                    'employee': employee,
                    'payslips': [],
                    'total_gross': 0,
                    'total_deduction': 0,
                    'total_payroll_deductions': 0,
                    'total_assessable': 0,
                    'total_pit': 0,
                    'month_work': 0
                }
            employee_data[employee.id]['month_work'] += 1
            employee_data[employee.id]['payslips'].append(payslip)

            gross_amount = self._calculate_gross_by_category(payslip)
            employee_data[employee.id]['total_gross'] += gross_amount

            pit_amount = self._calculate_pit_by_category(payslip)
            employee_data[employee.id]['total_pit'] += pit_amount

            payroll_deductions = self._calculate_deductions_by_category(payslip)
            if 'total_payroll_deductions' not in employee_data[employee.id]:
                employee_data[employee.id]['total_payroll_deductions'] = 0
            employee_data[employee.id]['total_payroll_deductions'] += payroll_deductions

        for emp_id, data in employee_data.items():
            employee = data['employee']

            monthly_deduction = self._get_tax_deduction_amount(employee)
            months_in_period = data['month_work']

            data['total_deduction'] = int(monthly_deduction * months_in_period)
            data['total_assessable'] = int(data['total_gross'] - data['total_deduction'])

            if data['total_assessable'] < 0:
                data['total_assessable'] = 0

            calculated_pit = self._calculate_personal_income_tax(data['total_assessable'])
            data['total_pit'] = int(calculated_pit)

            # Ensure all accumulated values are integers
            data['total_gross'] = int(data['total_gross'])
            data['total_payroll_deductions'] = int(data['total_payroll_deductions'])

        return employee_data

    def _get_payslip_data(self):
        year_start = f"{self.year}-01-01"
        year_end = f"{self.year}-12-31"

        payslips = self.env['hr.payslip'].search([
            ('state', '=', 'done'),
            ('date_to', '>=', year_start),
            ('date_to', '<=', year_end),
        ])

        if not payslips:
            raise UserError(_("No completed payslips found for the selected year."))

        data_KKTNCNE = self.calculateKKTNCNEReport(payslips)
        employee_data = {}

        for payslip in payslips:
            employee = payslip.employee_id
            if employee.id not in employee_data:
                employee_data[employee.id] = {
                    'employee': employee,
                    'payslips': [],
                    'total_annual_income': 0,
                    'total_deductions': 0,
                    'total_taxable_income': 0,
                    'total_pit_withheld': 0,
                    'tax_payable_refundable': 0,
                }

            employee_data[employee.id]['payslips'].append(payslip)

            gross_amount = self._get_gross_amount(payslip)
            employee_data[employee.id]['total_annual_income'] += gross_amount

            deduction_amount = self._get_deduction_amount(payslip)
            employee_data[employee.id]['total_deductions'] += deduction_amount

            taxable_income = self._get_taxable_income(payslip)
            employee_data[employee.id]['total_taxable_income'] += taxable_income

        for emp_id in employee_data.keys():
            if emp_id in data_KKTNCNE:
                employee_data[emp_id]['total_pit_withheld'] = int(data_KKTNCNE[emp_id]['total_pit'])

        for emp_id, data in employee_data.items():
            taxable_for_calculation = int(data['total_annual_income'] - data['total_deductions'])
            if taxable_for_calculation < 0:
                taxable_for_calculation = 0

            calculated_annual_tax = self._calculate_annual_personal_income_tax(taxable_for_calculation)
            data['tax_payable_refundable'] = int(calculated_annual_tax - data['total_pit_withheld'])

            # Ensure all accumulated values are integers
            data['total_annual_income'] = int(data['total_annual_income'])
            data['total_deductions'] = int(data['total_deductions'])
            data['total_taxable_income'] = int(data['total_taxable_income'])
            data['total_pit_withheld'] = int(data['total_pit_withheld'])

        return employee_data

    def _create_excel_file(self, employee_data):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('QTT-TNCN Report')

        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#D7E4BC'
        })

        data_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })

        number_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'num_format': '#,##0'
        })

        worksheet.set_column('A:A', 8)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 20)
        worksheet.set_column('E:E', 18)
        worksheet.set_column('F:F', 20)
        worksheet.set_column('G:G', 25)
        worksheet.set_column('H:H', 25)

        headers = [
            'No.',
            'Full Name',
            'Personal Tax Code',
            'Total Annual Income (VND)',
            'Total Deductions (VND)',
            'Taxable Income (VND)',
            'Total PIT Withheld (VND)',
            'Tax Payable/Refundable (VND)'
        ]

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        row = 1
        for emp_id, data in employee_data.items():
            employee = data['employee']

            worksheet.write(row, 0, row, data_format)
            worksheet.write(row, 1, employee.name or '', data_format)
            worksheet.write(row, 2, '', data_format)
            worksheet.write(row, 3, int(data['total_annual_income']), number_format)
            worksheet.write(row, 4, int(data['total_deductions']), number_format)
            worksheet.write(row, 5, int(data['total_taxable_income']), number_format)
            worksheet.write(row, 6, int(data['total_pit_withheld']), number_format)
            worksheet.write(row, 7, int(data['tax_payable_refundable']), number_format)

            row += 1

        workbook.close()
        output.seek(0)

        return output.getvalue()

    def export_qtt_tncn(self):
        try:
            employee_data = self._get_payslip_data()

            if not employee_data:
                raise UserError(_("No payslip data found for the selected year."))

            excel_data = self._create_excel_file(employee_data)

            filename = f"QTT-TNCN_{self.year}.xlsx"

            self.write({
                'export_file': base64.b64encode(excel_data),
                'export_filename': filename,
                'state': 'done'
            })

            return self.download_file()
        except Exception as e:
            raise UserError(_("Error generating QTT-TNCN report: %s") % str(e))

    def download_file(self):
        if not self.export_file:
            raise UserError(_("No file available for download."))

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/?model=hr.qtt.tncn.export&id={self.id}&field=export_file&download=true&filename={self.export_filename}',
            'target': 'self',
        }