from tcrm import models, fields, api
import base64
import io
from datetime import datetime

class PropertioReportExport(models.TransientModel):
    _name = 'propertio.report.export'
    _description = 'Export Propertio Reports'

    report_type = fields.Selection([
        ('collection_map', 'Sales & Collection Map'),
        ('gdv_analysis', 'Project GDV Analysis'),
        ('cashflow', 'Cash Flow Forecast')
    ], string='Report Type', required=True)

    export_format = fields.Selection([
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
        ('word', 'Word')
    ], string='Export Format', required=True, default='excel')

    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    
    file_data = fields.Binary(string='File', readonly=True)
    file_name = fields.Char(string='File Name', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft')

    def action_export(self, context=None):
        self.ensure_one()
        
        if self.export_format == 'excel':
            return self._export_excel()
        elif self.export_format == 'pdf':
            return self._export_pdf()
        elif self.export_format == 'word':
            return self._export_word()

    def _export_excel(self):
        """Export to Excel with color coding"""
        try:
            import xlsxwriter
        except ImportError:
            from tcrm.exceptions import UserError
            raise UserError('Please install xlsxwriter: pip install xlsxwriter')

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Define color formats
        paid_format = workbook.add_format({'bg_color': '#d4edda', 'font_color': '#155724'})
        overdue_format = workbook.add_format({'bg_color': '#f8d7da', 'font_color': '#721c24'})
        upcoming_format = workbook.add_format({'bg_color': '#fff3cd', 'font_color': '#856404'})
        future_format = workbook.add_format({'bg_color': '#e2e3e5', 'font_color': '#383d41'})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white'})
        
        if self.report_type == 'collection_map':
            self._write_collection_map(workbook, header_format, paid_format, overdue_format, upcoming_format, future_format)
        elif self.report_type == 'gdv_analysis':
            self._write_gdv_analysis(workbook, header_format)
        elif self.report_type == 'cashflow':
            self._write_cashflow(workbook, header_format)
        
        workbook.close()
        output.seek(0)
        
        self.write({
            'file_data': base64.b64encode(output.read()),
            'file_name': f'{self.report_type}_{datetime.now().strftime("%Y%m%d")}.xlsx',
            'state': 'done'
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'propertio.report.export',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def _write_collection_map(self, workbook, header_fmt, paid_fmt, overdue_fmt, upcoming_fmt, future_fmt):
        worksheet = workbook.add_worksheet('Collection Map')
        
        headers = ['Contract', 'Customer', 'Description', 'Due Date', 'Amount', 'Paid', 'Balance', 'Status']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_fmt)
        
        domain = []
        if self.date_from:
            domain.append(('date_due', '>=', self.date_from))
        if self.date_to:
            domain.append(('date_due', '<=', self.date_to))
        
        installments = self.env['propertio.installment'].search(domain, order='date_due')
        
        row = 1
        for inst in installments:
            status_format = {
                'paid': paid_fmt,
                'overdue': overdue_fmt,
                'upcoming': upcoming_fmt,
                'future': future_fmt
            }.get(inst.payment_status, None)
            
            worksheet.write(row, 0, inst.sale_id.name)
            worksheet.write(row, 1, inst.partner_id.name)
            worksheet.write(row, 2, inst.name)
            worksheet.write(row, 3, str(inst.date_due))
            worksheet.write(row, 4, inst.amount)
            worksheet.write(row, 5, inst.amount_paid)
            worksheet.write(row, 6, inst.residual)
            worksheet.write(row, 7, inst.payment_status.upper(), status_format)
            row += 1

    def _write_gdv_analysis(self, workbook, header_fmt):
        worksheet = workbook.add_worksheet('GDV Analysis')
        
        headers = ['Project', 'Category', 'State', 'Units', 'List Price', 'Sold Value', 'Collected', 'Receivable']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_fmt)
        
        units = self.env['propertio.unit'].search([])
        
        row = 1
        for unit in units:
            worksheet.write(row, 0, unit.project_id.name)
            worksheet.write(row, 1, unit.category_id.name if unit.category_id else '')
            worksheet.write(row, 2, unit.state.upper())
            worksheet.write(row, 3, 1)
            worksheet.write(row, 4, unit.list_price)
            worksheet.write(row, 5, unit.sold_value)
            worksheet.write(row, 6, unit.collected_amount)
            worksheet.write(row, 7, unit.receivable_amount)
            row += 1

    def _write_cashflow(self, workbook, header_fmt):
        worksheet = workbook.add_worksheet('Cash Flow')
        
        headers = ['Month', 'Expected', 'Actual', 'Variance']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_fmt)
        
        # Group by month
        self.env.cr.execute("""
            SELECT 
                DATE_TRUNC('month', date_due) as month,
                SUM(amount) as expected,
                SUM(amount_paid) as actual
            FROM propertio_installment
            WHERE date_due IS NOT NULL
            GROUP BY DATE_TRUNC('month', date_due)
            ORDER BY month
        """)
        
        row = 1
        for record in self.env.cr.fetchall():
            month, expected, actual = record
            variance = actual - expected
            worksheet.write(row, 0, str(month.strftime('%Y-%m')))
            worksheet.write(row, 1, expected or 0)
            worksheet.write(row, 2, actual or 0)
            worksheet.write(row, 3, variance)
            row += 1

    def _export_pdf(self):
        """Generate PDF report"""
        return self.env.ref('tcrm_propertio.action_report_export_pdf').report_action(self)

    def _export_word(self):
        """Generate Word document"""
        from tcrm.http import request
        
        html_content = self._generate_html_report()
        filename = f'{self.report_type}_{datetime.now().strftime("%Y%m%d")}.doc'
        
        self.write({
            'file_data': base64.b64encode(html_content.encode('utf-8')),
            'file_name': filename,
            'state': 'done'
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'propertio.report.export',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def _generate_html_report(self):
        """Generate HTML content for Word export"""
        return f"""
        <html>
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4472C4; color: white; }}
                .paid {{ background-color: #d4edda; }}
                .overdue {{ background-color: #f8d7da; }}
                .upcoming {{ background-color: #fff3cd; }}
                .future {{ background-color: #e2e3e5; }}
            </style>
        </head>
        <body>
            <h1>{self.report_type.replace('_', ' ').title()}</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            {self._get_report_table_html()}
        </body>
        </html>
        """

    def _get_report_table_html(self):
        if self.report_type == 'collection_map':
            installments = self.env['propertio.installment'].search([])
            rows = ''
            for inst in installments:
                status_class = inst.payment_status
                rows += f"""
                <tr class="{status_class}">
                    <td>{inst.sale_id.name}</td>
                    <td>{inst.partner_id.name}</td>
                    <td>{inst.name}</td>
                    <td>{inst.date_due}</td>
                    <td>{inst.amount}</td>
                    <td>{inst.payment_status.upper()}</td>
                </tr>
                """
            return f"""
            <table>
                <thead>
                    <tr>
                        <th>Contract</th>
                        <th>Customer</th>
                        <th>Description</th>
                        <th>Due Date</th>
                        <th>Amount</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            """
        return "<p>Report data</p>"

    def action_download(self, context=None):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=propertio.report.export&id={self.id}&field=file_data&download=true&filename={self.file_name}',
            'target': 'self',
        }
