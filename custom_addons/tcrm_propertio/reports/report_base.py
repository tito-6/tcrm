# -*- coding: utf-8 -*-
"""
Propertio Report Base - Unified Report Infrastructure
Supports: XLSX (Excel), CSV, PDF (via reportlab), HTML exports
All exports maintain consistent colors and layouts
"""

import base64
import io
import csv
from datetime import datetime, date

# Color scheme for payment status
COLORS = {
    'paid': {'bg': '#28a745', 'fg': '#ffffff', 'bg_light': '#d4edda', 'fg_dark': '#155724'},
    'overdue': {'bg': '#dc3545', 'fg': '#ffffff', 'bg_light': '#f8d7da', 'fg_dark': '#721c24'},
    'upcoming': {'bg': '#ffc107', 'fg': '#212529', 'bg_light': '#fff3cd', 'fg_dark': '#856404'},
    'future': {'bg': '#6c757d', 'fg': '#ffffff', 'bg_light': '#e2e3e5', 'fg_dark': '#383d41'},
    'header': {'bg': '#1a365d', 'fg': '#ffffff'},
    'subheader': {'bg': '#2c5282', 'fg': '#ffffff'},
    'total': {'bg': '#edf2f7', 'fg': '#1a202c'},
}

# Unit status colors
UNIT_COLORS = {
    'available': {'bg': '#48bb78', 'fg': '#ffffff'},
    'reserved': {'bg': '#ed8936', 'fg': '#ffffff'},
    'sold': {'bg': '#4299e1', 'fg': '#ffffff'},
    'rented': {'bg': '#9f7aea', 'fg': '#ffffff'},
}


class ReportStyleMixin:
    """Mixin providing consistent styling across all export formats"""
    
    @staticmethod
    def get_excel_formats(workbook):
        """Create Excel formats with consistent colors"""
        formats = {
            'header': workbook.add_format({
                'bold': True, 'bg_color': COLORS['header']['bg'], 
                'font_color': COLORS['header']['fg'], 'border': 1,
                'align': 'center', 'valign': 'vcenter', 'font_size': 11
            }),
            'subheader': workbook.add_format({
                'bold': True, 'bg_color': COLORS['subheader']['bg'],
                'font_color': COLORS['subheader']['fg'], 'border': 1
            }),
            'total': workbook.add_format({
                'bold': True, 'bg_color': COLORS['total']['bg'],
                'font_color': COLORS['total']['fg'], 'border': 1,
                'num_format': '#,##0.00'
            }),
            'currency': workbook.add_format({
                'num_format': '#,##0.00', 'border': 1
            }),
            'date': workbook.add_format({
                'num_format': 'yyyy-mm-dd', 'border': 1
            }),
            'percent': workbook.add_format({
                'num_format': '0.00%', 'border': 1
            }),
            'normal': workbook.add_format({'border': 1}),
        }
        
        # Status formats
        for status, colors in COLORS.items():
            if status in ['paid', 'overdue', 'upcoming', 'future']:
                formats[f'status_{status}'] = workbook.add_format({
                    'bg_color': colors['bg_light'], 
                    'font_color': colors['fg_dark'],
                    'border': 1, 'bold': True, 'align': 'center'
                })
                formats[f'row_{status}'] = workbook.add_format({
                    'bg_color': colors['bg_light'],
                    'border': 1
                })
        
        # Unit status formats
        for status, colors in UNIT_COLORS.items():
            formats[f'unit_{status}'] = workbook.add_format({
                'bg_color': colors['bg'], 'font_color': colors['fg'],
                'border': 1, 'bold': True, 'align': 'center'
            })
        
        return formats
    
    @staticmethod
    def get_html_styles():
        """Get consistent HTML/CSS styles for reports"""
        return """
        <style>
            @page { size: A4 landscape; margin: 10mm; }
            * { box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 12px;
                color: #1a202c;
                line-height: 1.4;
                margin: 0;
                padding: 20px;
            }
            .report-container { max-width: 100%; margin: 0 auto; }
            .report-header {
                background: linear-gradient(135deg, #1a365d 0%, #2c5282 100%);
                color: white;
                padding: 20px;
                border-radius: 8px 8px 0 0;
                margin-bottom: 0;
            }
            .report-header h1 { margin: 0 0 10px 0; font-size: 24px; }
            .report-header .meta { font-size: 12px; opacity: 0.9; }
            .report-filters {
                background: #edf2f7;
                padding: 10px 20px;
                border-bottom: 1px solid #e2e8f0;
                font-size: 11px;
            }
            table { 
                width: 100%; 
                border-collapse: collapse; 
                margin-top: 0;
                background: white;
            }
            th { 
                background: #2c5282; 
                color: white; 
                padding: 12px 8px;
                text-align: left;
                font-weight: 600;
                border: 1px solid #1a365d;
                font-size: 11px;
            }
            td { 
                padding: 8px; 
                border: 1px solid #e2e8f0;
                font-size: 11px;
            }
            tr:nth-child(even) { background: #f7fafc; }
            tr:hover { background: #edf2f7; }
            
            /* Status badges */
            .badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-weight: 600;
                font-size: 10px;
                text-transform: uppercase;
            }
            .badge-paid { background: #d4edda; color: #155724; }
            .badge-overdue { background: #f8d7da; color: #721c24; }
            .badge-upcoming { background: #fff3cd; color: #856404; }
            .badge-future { background: #e2e3e5; color: #383d41; }
            
            /* Unit status */
            .badge-available { background: #48bb78; color: white; }
            .badge-reserved { background: #ed8936; color: white; }
            .badge-sold { background: #4299e1; color: white; }
            .badge-rented { background: #9f7aea; color: white; }
            
            /* Row coloring by status */
            tr.row-paid { background: #d4edda !important; }
            tr.row-overdue { background: #f8d7da !important; }
            tr.row-upcoming { background: #fff3cd !important; }
            tr.row-future { background: #e2e3e5 !important; }
            
            /* Totals row */
            tr.total-row { 
                background: #edf2f7 !important; 
                font-weight: bold;
            }
            tr.total-row td { border-top: 2px solid #2c5282; }
            
            /* Summary cards */
            .summary-cards {
                display: flex;
                gap: 15px;
                margin: 20px 0;
                flex-wrap: wrap;
            }
            .summary-card {
                flex: 1;
                min-width: 150px;
                background: white;
                border-radius: 8px;
                padding: 15px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .summary-card .label { 
                font-size: 11px; 
                color: #718096; 
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .summary-card .value { 
                font-size: 24px; 
                font-weight: bold; 
                color: #1a365d;
                margin-top: 5px;
            }
            .summary-card.success .value { color: #28a745; }
            .summary-card.danger .value { color: #dc3545; }
            .summary-card.warning .value { color: #ffc107; }
            
            /* Currency formatting */
            .currency { text-align: right; font-family: 'Consolas', monospace; }
            .positive { color: #28a745; }
            .negative { color: #dc3545; }
            
            /* Print styles */
            @media print {
                body { padding: 0; }
                .report-header { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                th { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                .badge { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                tr.row-paid, tr.row-overdue, tr.row-upcoming, tr.row-future {
                    -webkit-print-color-adjust: exact; print-color-adjust: exact;
                }
                .no-print { display: none; }
            }
        </style>
        """
    
    @staticmethod
    def get_pdf_colors():
        """Get colors for reportlab PDF generation"""
        from reportlab.lib.colors import HexColor
        return {
            'header_bg': HexColor('#1a365d'),
            'header_fg': HexColor('#ffffff'),
            'paid': HexColor('#d4edda'),
            'overdue': HexColor('#f8d7da'),
            'upcoming': HexColor('#fff3cd'),
            'future': HexColor('#e2e3e5'),
            'border': HexColor('#e2e8f0'),
            'text': HexColor('#1a202c'),
        }


class BaseReportData:
    """Base class for report data generation"""
    
    def __init__(self, env, date_from=None, date_to=None, **kwargs):
        company = env.company
        ctx = dict(env.context, allowed_company_ids=[company.id], force_company=company.id)
        self.env = env["res.users"].with_context(ctx).env
        self.company_id = company.id
        self.date_from = date_from
        self.date_to = date_to
        self.options = kwargs
        self.generated_at = datetime.now()

    def secure_domain(self, model_name, domain=None):
        """Append strict tenant filter when model has company_id."""
        dom = list(domain or [])
        model = self.env[model_name]
        if 'company_id' in model._fields:
            dom.append(('company_id', '=', self.company_id))
        return dom
    
    def get_title(self):
        """Override in subclass"""
        return "Report"
    
    def get_headers(self):
        """Override in subclass - return list of column headers"""
        return []
    
    def get_data(self):
        """Override in subclass - return list of row data"""
        return []
    
    def get_summary(self):
        """Override in subclass - return summary data dict"""
        return {}
    
    def get_column_widths(self):
        """Override in subclass - return list of column widths for Excel"""
        return [15] * len(self.get_headers())
    
    def format_currency(self, value, currency='USD'):
        """Format currency value with symbol (legacy helper)."""
        if value is None:
            return ''
        symbol = currency if isinstance(currency, str) else getattr(currency, 'symbol', None) or getattr(currency, 'name', '') or ''
        try:
            amount = float(value)
        except (TypeError, ValueError):
            return str(value)
        # TR-style thousands/decimal when symbol is ₺
        if symbol in ('₺', 'TL', 'TRY'):
            formatted = f"{amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            return f"{symbol} {formatted}"
        return f"{symbol} {amount:,.2f}".strip()
    
    def format_date(self, value):
        """Format date value"""
        if value is None:
            return ''
        if isinstance(value, (datetime, date)):
            return value.strftime('%Y-%m-%d')
        return str(value)
    
    def format_percent(self, value):
        """Format percentage value"""
        if value is None:
            return ''
        return f"{value:.1f}%"
