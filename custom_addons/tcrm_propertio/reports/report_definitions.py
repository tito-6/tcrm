# -*- coding: utf-8 -*-
"""
Propertio Report Definitions - All 28 Real Estate Reports
Each report class defines its data structure, queries, and formatting
"""

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from .report_base import BaseReportData


class SalesCollectionSummaryReport(BaseReportData):
    """1. Sales Collection Summary - Shows collected vs planned amounts"""
    
    def get_title(self):
        return "Sales Collection Summary Report"
    
    def get_headers(self):
        return ['Contract', 'Customer', 'Unit', 'Sale Value', 'Collected', 'Outstanding', 'Collection %', 'Payment Status']
    
    def get_column_widths(self):
        return [15, 20, 15, 15, 15, 15, 12, 15]
    
    def get_data(self):
        domain = []
        if self.date_from:
            domain.append(('date_order', '>=', self.date_from))
        if self.date_to:
            domain.append(('date_order', '<=', self.date_to))
        
        sales = self.env['propertio.sale'].search(self.secure_domain('propertio.sale', domain))
        data = []
        
        for sale in sales:
            collected = sum(sale.installment_ids.filtered(lambda x: x.is_paid).mapped('amount'))
            total = sale.total_amount or 0
            outstanding = total - collected
            collection_pct = (collected / total * 100) if total else 0
            
            # Determine status
            overdue_count = len(sale.installment_ids.filtered(lambda x: x.payment_status == 'overdue'))
            status = 'Overdue' if overdue_count > 0 else ('Paid' if collection_pct >= 100 else 'Active')
            
            data.append({
                'Contract': sale.name or '',
                'Customer': sale.partner_id.name or '',
                'Unit': sale.unit_id.name or '',
                'Sale Value': total,
                'Collected': collected,
                'Outstanding': outstanding,
                'Collection %': f"{collection_pct:.1f}%",
                'Payment Status': status,
                '_status': status.lower()
            })
        
        return data
    
    def get_summary(self):
        data = self.get_data()
        total_value = sum(d['Sale Value'] for d in data)
        total_collected = sum(d['Collected'] for d in data)
        total_outstanding = sum(d['Outstanding'] for d in data)
        
        return {
            'Total Sales Value': total_value,
            'Total Collected': total_collected,
            'Total Outstanding': total_outstanding,
            'Collection Rate': f"{(total_collected/total_value*100) if total_value else 0:.1f}%"
        }


class TypeBasedSalesReport(BaseReportData):
    """2. Type-Based Sales & Inventory Analysis"""
    
    def get_title(self):
        return "Type-Based Sales & Inventory Analysis"
    
    def get_headers(self):
        return ['Unit Type', 'Total Units', 'Available', 'Reserved', 'Sold', 'Total Stock Value', 'Sold Value', 'Available Value']
    
    def get_column_widths(self):
        return [15, 12, 12, 12, 12, 18, 18, 18]
    
    def get_data(self):
        # Group units by category
        units = self.env['propertio.unit'].search(self.secure_domain('propertio.unit'))
        categories = {}
        
        for unit in units:
            cat_name = unit.category_id.name if unit.category_id else 'Uncategorized'
            if cat_name not in categories:
                categories[cat_name] = {
                    'total': 0, 'available': 0, 'reserved': 0, 'sold': 0,
                    'stock_value': 0, 'sold_value': 0, 'available_value': 0
                }
            
            categories[cat_name]['total'] += 1
            categories[cat_name]['stock_value'] += unit.list_price or 0
            
            if unit.state == 'available':
                categories[cat_name]['available'] += 1
                categories[cat_name]['available_value'] += unit.list_price or 0
            elif unit.state == 'reserved':
                categories[cat_name]['reserved'] += 1
            elif unit.state == 'sold':
                categories[cat_name]['sold'] += 1
                categories[cat_name]['sold_value'] += unit.sold_value or unit.list_price or 0
        
        data = []
        for cat_name, stats in categories.items():
            data.append({
                'Unit Type': cat_name,
                'Total Units': stats['total'],
                'Available': stats['available'],
                'Reserved': stats['reserved'],
                'Sold': stats['sold'],
                'Total Stock Value': stats['stock_value'],
                'Sold Value': stats['sold_value'],
                'Available Value': stats['available_value']
            })
        
        return sorted(data, key=lambda x: x['Sold'], reverse=True)
    
    def get_summary(self):
        data = self.get_data()
        return {
            'Total Unit Types': len(data),
            'Total Units': sum(d['Total Units'] for d in data),
            'Total Available': sum(d['Available'] for d in data),
            'Total Sold': sum(d['Sold'] for d in data)
        }


class CustomerJourneyReport(BaseReportData):
    """3. Customer Journey - Lead to Sale tracking"""
    
    def get_title(self):
        return "Customer Journey Report"
    
    def get_headers(self):
        return ['Customer', 'First Contact', 'Lead Source', 'Visits', 'Offers Made', 'Sales', 'Total Value', 'Status']
    
    def get_column_widths(self):
        return [20, 12, 15, 10, 12, 10, 15, 12]
    
    def get_data(self):
        partners = self.env['res.partner'].search(self.secure_domain('res.partner', [('is_company', '=', False)]))
        data = []
        
        for partner in partners:
            sales = self.env['propertio.sale'].search(self.secure_domain('propertio.sale', [('partner_id', '=', partner.id)]))
            if not sales:
                continue
            
            total_value = sum(s.total_amount or 0 for s in sales)
            first_sale = min(sales.mapped('date_order')) if sales else None
            
            data.append({
                'Customer': partner.name,
                'First Contact': self.format_date(first_sale),
                'Lead Source': partner.ref or 'Direct',
                'Visits': '-',
                'Offers Made': len(sales),
                'Sales': len(sales.filtered(lambda s: s.state == 'sale')),
                'Total Value': total_value,
                'Status': 'Active' if sales else 'Lead'
            })
        
        return sorted(data, key=lambda x: x['Total Value'], reverse=True)[:100]


class SalesReport(BaseReportData):
    """4. Sales Report - Classic sales performance"""
    
    def get_title(self):
        return "Sales Report"
    
    def get_headers(self):
        return ['Contract', 'Date', 'Customer', 'Project', 'Unit', 'Sale Price', 'Discount', 'Net Amount', 'Status']
    
    def get_column_widths(self):
        return [15, 12, 20, 15, 12, 15, 12, 15, 12]
    
    def get_data(self):
        domain = []
        if self.date_from:
            domain.append(('date_order', '>=', self.date_from))
        if self.date_to:
            domain.append(('date_order', '<=', self.date_to))
        
        sales = self.env['propertio.sale'].search(self.secure_domain('propertio.sale', domain), order='date_order desc')
        data = []
        
        for sale in sales:
            list_price = sale.unit_id.list_price or 0
            sale_price = sale.total_amount or 0
            discount = list_price - sale_price
            
            data.append({
                'Contract': sale.name or '',
                'Date': self.format_date(sale.date_order),
                'Customer': sale.partner_id.name or '',
                'Project': sale.unit_id.project_id.name if sale.unit_id else '',
                'Unit': sale.unit_id.name if sale.unit_id else '',
                'Sale Price': list_price,
                'Discount': discount,
                'Net Amount': sale_price,
                'Status': sale.state.title() if sale.state else ''
            })
        
        return data
    
    def get_summary(self):
        data = self.get_data()
        return {
            'Total Sales': len(data),
            'Total Value': sum(d['Net Amount'] for d in data),
            'Total Discounts': sum(d['Discount'] for d in data),
            'Avg Sale Value': sum(d['Net Amount'] for d in data) / len(data) if data else 0
        }


class CashRegisterReport(BaseReportData):
    """5. A & B Cash Register Report"""
    
    def get_title(self):
        return "Cash Register Report"
    
    def get_headers(self):
        return ['Date', 'Receipt #', 'Customer', 'Contract', 'Amount', 'Payment Method', 'Register', 'Reference']
    
    def get_column_widths(self):
        return [12, 15, 20, 15, 15, 15, 12, 15]
    
    def get_data(self):
        domain = []
        if self.date_from:
            domain.append(('payment_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('payment_date', '<=', self.date_to))
        
        payments = self.env['propertio.payment'].search(self.secure_domain('propertio.payment', domain), order='payment_date desc')
        data = []
        
        for payment in payments:
            data.append({
                'Date': self.format_date(payment.payment_date),
                'Receipt #': payment.name or '',
                'Customer': payment.partner_id.name or '',
                'Contract': payment.sale_id.name if payment.sale_id else '',
                'Amount': payment.amount or 0,
                'Payment Method': payment.payment_method or 'Cash',
                'Register': 'A',  # Can be extended
                'Reference': payment.reference or ''
            })
        
        return data
    
    def get_summary(self):
        data = self.get_data()
        return {
            'Total Receipts': len(data),
            'Total Amount': sum(d['Amount'] for d in data)
        }


class ApprovalBasedSalesChart(BaseReportData):
    """6. Approval-Based Sales Chart"""
    
    def get_title(self):
        return "Approval-Based Sales Analysis"
    
    def get_headers(self):
        return ['Status', 'Count', 'Total Value', 'Avg Value', 'Percentage']
    
    def get_column_widths(self):
        return [15, 12, 18, 18, 12]
    
    def get_data(self):
        sales = self.env['propertio.sale'].search(self.secure_domain('propertio.sale'))
        
        status_groups = {}
        for sale in sales:
            status = sale.state or 'draft'
            if status not in status_groups:
                status_groups[status] = {'count': 0, 'value': 0}
            status_groups[status]['count'] += 1
            status_groups[status]['value'] += sale.total_amount or 0
        
        total_count = sum(g['count'] for g in status_groups.values())
        
        data = []
        for status, stats in status_groups.items():
            data.append({
                'Status': status.title(),
                'Count': stats['count'],
                'Total Value': stats['value'],
                'Avg Value': stats['value'] / stats['count'] if stats['count'] else 0,
                'Percentage': f"{(stats['count'] / total_count * 100) if total_count else 0:.1f}%"
            })
        
        return sorted(data, key=lambda x: x['Count'], reverse=True)


class TotalSalesChartReport(BaseReportData):
    """7. Total Sales Chart - Trend over time"""
    
    def get_title(self):
        return "Total Sales Chart Report"
    
    def get_headers(self):
        return ['Period', 'Sales Count', 'Total Value', 'Avg Value', 'Growth %']
    
    def get_column_widths(self):
        return [15, 12, 18, 18, 12]
    
    def get_data(self):
        # Last 12 months
        sales = self.env['propertio.sale'].search(self.secure_domain('propertio.sale'))
        
        monthly_data = {}
        for sale in sales:
            if not sale.date_order:
                continue
            month_key = sale.date_order.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {'count': 0, 'value': 0}
            monthly_data[month_key]['count'] += 1
            monthly_data[month_key]['value'] += sale.total_amount or 0
        
        data = []
        sorted_months = sorted(monthly_data.keys())
        prev_value = 0
        
        for month in sorted_months[-12:]:  # Last 12 months
            stats = monthly_data[month]
            growth = ((stats['value'] - prev_value) / prev_value * 100) if prev_value else 0
            
            data.append({
                'Period': month,
                'Sales Count': stats['count'],
                'Total Value': stats['value'],
                'Avg Value': stats['value'] / stats['count'] if stats['count'] else 0,
                'Growth %': f"{growth:+.1f}%" if prev_value else '-'
            })
            prev_value = stats['value']
        
        return data


class IncomingPaymentsChartReport(BaseReportData):
    """8. Incoming & Expected Payments Chart"""
    
    def get_title(self):
        return "Incoming & Expected Payments Forecast"
    
    def get_headers(self):
        return ['Month', 'Expected Amount', 'Received Amount', 'Variance', 'Collection Rate']
    
    def get_column_widths(self):
        return [15, 18, 18, 15, 15]
    
    def get_data(self):
        self.env.cr.execute("""
            SELECT 
                TO_CHAR(date_due, 'YYYY-MM') as month,
                SUM(amount) as expected,
                SUM(amount_paid) as received
            FROM propertio_installment
            WHERE date_due IS NOT NULL
              AND company_id = %s
            GROUP BY TO_CHAR(date_due, 'YYYY-MM')
            ORDER BY month
        """, [self.company_id])
        
        data = []
        for row in self.env.cr.fetchall():
            month, expected, received = row
            expected = expected or 0
            received = received or 0
            variance = received - expected
            rate = (received / expected * 100) if expected else 0
            
            data.append({
                'Month': month,
                'Expected Amount': expected,
                'Received Amount': received,
                'Variance': variance,
                'Collection Rate': f"{rate:.1f}%"
            })
        
        return data[-12:]  # Last 12 months


class EndOfDayMeetingReport(BaseReportData):
    """9. End-of-Day Meeting Report"""
    
    def get_title(self):
        return "End-of-Day Meeting Report"
    
    def get_headers(self):
        return ['Date', 'Salesperson', 'New Leads', 'Meetings', 'Follow-ups', 'Sales Made', 'Sales Value']
    
    def get_column_widths(self):
        return [12, 18, 12, 12, 12, 12, 18]
    
    def get_data(self):
        # Placeholder - would need CRM integration
        today = date.today()
        
        # Get sales by user for today
        domain = [('date_order', '=', today)]
        sales = self.env['propertio.sale'].search(self.secure_domain('propertio.sale', domain))
        
        user_stats = {}
        for sale in sales:
            user = sale.user_id.name if sale.user_id else 'Unassigned'
            if user not in user_stats:
                user_stats[user] = {'count': 0, 'value': 0}
            user_stats[user]['count'] += 1
            user_stats[user]['value'] += sale.total_amount or 0
        
        data = []
        for user, stats in user_stats.items():
            data.append({
                'Date': self.format_date(today),
                'Salesperson': user,
                'New Leads': '-',
                'Meetings': '-',
                'Follow-ups': '-',
                'Sales Made': stats['count'],
                'Sales Value': stats['value']
            })
        
        return data if data else [{'Date': self.format_date(today), 'Salesperson': 'No activity', 'New Leads': 0, 'Meetings': 0, 'Follow-ups': 0, 'Sales Made': 0, 'Sales Value': 0}]


class DailySalesQuantityReport(BaseReportData):
    """10. Daily Sales Quantity Report"""
    
    def get_title(self):
        return "Daily Sales Quantity Report"
    
    def get_headers(self):
        return ['Date', 'Day', 'Units Sold', 'Total Value', 'Avg Unit Price']
    
    def get_column_widths(self):
        return [12, 12, 12, 18, 18]
    
    def get_data(self):
        domain = []
        if self.date_from:
            domain.append(('date_order', '>=', self.date_from))
        if self.date_to:
            domain.append(('date_order', '<=', self.date_to))
        
        sales = self.env['propertio.sale'].search(self.secure_domain('propertio.sale', domain))
        
        daily_data = {}
        for sale in sales:
            if not sale.date_order:
                continue
            day_key = sale.date_order
            if day_key not in daily_data:
                daily_data[day_key] = {'count': 0, 'value': 0}
            daily_data[day_key]['count'] += 1
            daily_data[day_key]['value'] += sale.total_amount or 0
        
        data = []
        for day, stats in sorted(daily_data.items(), reverse=True):
            data.append({
                'Date': self.format_date(day),
                'Day': day.strftime('%A'),
                'Units Sold': stats['count'],
                'Total Value': stats['value'],
                'Avg Unit Price': stats['value'] / stats['count'] if stats['count'] else 0
            })
        
        return data[:30]  # Last 30 days


class CashFlowStatementReport(BaseReportData):
    """11. Cash Flow Statement"""
    
    def get_title(self):
        return "Cash Flow Statement"
    
    def get_headers(self):
        return ['Period', 'Opening Balance', 'Cash Inflows', 'Cash Outflows', 'Net Cash Flow', 'Closing Balance']
    
    def get_column_widths(self):
        return [15, 18, 18, 18, 18, 18]
    
    def get_data(self):
        # Get payment data grouped by month
        self.env.cr.execute("""
            SELECT 
                TO_CHAR(payment_date, 'YYYY-MM') as month,
                SUM(amount) as inflows
            FROM propertio_payment
            WHERE payment_date IS NOT NULL
              AND company_id = %s
            GROUP BY TO_CHAR(payment_date, 'YYYY-MM')
            ORDER BY month
        """, [self.company_id])
        
        data = []
        running_balance = 0
        
        for row in self.env.cr.fetchall():
            month, inflows = row
            inflows = inflows or 0
            outflows = 0  # Would need expense tracking
            net_flow = inflows - outflows
            opening = running_balance
            closing = opening + net_flow
            
            data.append({
                'Period': month,
                'Opening Balance': opening,
                'Cash Inflows': inflows,
                'Cash Outflows': outflows,
                'Net Cash Flow': net_flow,
                'Closing Balance': closing
            })
            running_balance = closing
        
        return data[-12:]


class EmployeePerformanceReport(BaseReportData):
    """12. Employee Performance Report"""
    
    def get_title(self):
        return "Employee Performance Report"
    
    def get_headers(self):
        return ['Salesperson', 'Deals', 'Total Revenue', 'Avg Deal Size', 'Collection Amount', 'Collection Rate', 'Rank']
    
    def get_column_widths(self):
        return [20, 10, 18, 18, 18, 15, 10]
    
    def get_data(self):
        domain = []
        if self.date_from:
            domain.append(('date_order', '>=', self.date_from))
        if self.date_to:
            domain.append(('date_order', '<=', self.date_to))
        
        sales = self.env['propertio.sale'].search(self.secure_domain('propertio.sale', domain))
        
        user_stats = {}
        for sale in sales:
            user = sale.user_id.name if sale.user_id else 'Unassigned'
            if user not in user_stats:
                user_stats[user] = {'deals': 0, 'revenue': 0, 'collected': 0}
            user_stats[user]['deals'] += 1
            user_stats[user]['revenue'] += sale.total_amount or 0
            user_stats[user]['collected'] += sum(sale.installment_ids.filtered(lambda x: x.is_paid).mapped('amount'))
        
        data = []
        for user, stats in user_stats.items():
            rate = (stats['collected'] / stats['revenue'] * 100) if stats['revenue'] else 0
            data.append({
                'Salesperson': user,
                'Deals': stats['deals'],
                'Total Revenue': stats['revenue'],
                'Avg Deal Size': stats['revenue'] / stats['deals'] if stats['deals'] else 0,
                'Collection Amount': stats['collected'],
                'Collection Rate': f"{rate:.1f}%",
                '_sort_key': stats['revenue']
            })
        
        # Sort by revenue and add rank
        data = sorted(data, key=lambda x: x.get('_sort_key', 0), reverse=True)
        for i, row in enumerate(data, 1):
            row['Rank'] = i
            del row['_sort_key']
        
        return data


class SalesStatusReport(BaseReportData):
    """13. Sales Status Report"""
    
    def get_title(self):
        return "Sales Status Report"
    
    def get_headers(self):
        return ['Contract', 'Customer', 'Unit', 'Sale Date', 'Amount', 'Paid', 'Balance', 'Status']
    
    def get_column_widths(self):
        return [15, 20, 15, 12, 15, 15, 15, 12]
    
    def get_data(self):
        sales = self.env['propertio.sale'].search(self.secure_domain('propertio.sale'), order='date_order desc')
        data = []
        
        for sale in sales:
            paid = sum(sale.installment_ids.filtered(lambda x: x.is_paid).mapped('amount'))
            total = sale.total_amount or 0
            balance = total - paid
            
            # Determine status
            if balance <= 0:
                status = 'Paid'
            elif sale.state == 'cancel':
                status = 'Cancelled'
            elif any(i.payment_status == 'overdue' for i in sale.installment_ids):
                status = 'Overdue'
            else:
                status = 'Active'
            
            data.append({
                'Contract': sale.name or '',
                'Customer': sale.partner_id.name or '',
                'Unit': sale.unit_id.name if sale.unit_id else '',
                'Sale Date': self.format_date(sale.date_order),
                'Amount': total,
                'Paid': paid,
                'Balance': balance,
                'Status': status,
                '_status': status.lower()
            })
        
        return data


class PaymentPlanTableReport(BaseReportData):
    """14. Payment Plan Table"""
    
    def get_title(self):
        return "Payment Plan Table"
    
    def get_headers(self):
        return ['Contract', 'Customer', 'Installment', 'Due Date', 'Amount', 'Paid', 'Balance', 'Status']
    
    def get_column_widths(self):
        return [15, 20, 15, 12, 15, 15, 15, 12]
    
    def get_data(self):
        domain = []
        if self.date_from:
            domain.append(('date_due', '>=', self.date_from))
        if self.date_to:
            domain.append(('date_due', '<=', self.date_to))
        
        installments = self.env['propertio.installment'].search(self.secure_domain('propertio.installment', domain), order='date_due')
        data = []
        
        for inst in installments:
            data.append({
                'Contract': inst.sale_id.name if inst.sale_id else '',
                'Customer': inst.partner_id.name or '',
                'Installment': inst.name or '',
                'Due Date': self.format_date(inst.date_due),
                'Amount': inst.amount or 0,
                'Paid': inst.amount_paid or 0,
                'Balance': inst.residual or 0,
                'Status': inst.payment_status.title() if inst.payment_status else '',
                '_status': inst.payment_status or ''
            })
        
        return data


class ExpectedPaymentListReport(BaseReportData):
    """15. Expected Payment List"""
    
    def get_title(self):
        return "Expected Payment List"
    
    def get_headers(self):
        return ['Due Date', 'Days Until Due', 'Contract', 'Customer', 'Installment', 'Amount Due', 'Status']
    
    def get_column_widths(self):
        return [12, 15, 15, 20, 15, 15, 12]
    
    def get_data(self):
        today = date.today()
        
        domain = [('is_paid', '=', False)]
        if self.date_from:
            domain.append(('date_due', '>=', self.date_from))
        if self.date_to:
            domain.append(('date_due', '<=', self.date_to))
        
        installments = self.env['propertio.installment'].search(self.secure_domain('propertio.installment', domain), order='date_due')
        data = []
        
        for inst in installments:
            days_until = (inst.date_due - today).days if inst.date_due else 0
            
            data.append({
                'Due Date': self.format_date(inst.date_due),
                'Days Until Due': days_until,
                'Contract': inst.sale_id.name if inst.sale_id else '',
                'Customer': inst.partner_id.name or '',
                'Installment': inst.name or '',
                'Amount Due': inst.residual or inst.amount or 0,
                'Status': inst.payment_status.title() if inst.payment_status else '',
                '_status': inst.payment_status or ''
            })
        
        return data


class AuthorizationMatrixReport(BaseReportData):
    """16. Authorization Matrix"""
    
    def get_title(self):
        return "Authorization Matrix"
    
    def get_headers(self):
        return ['Action', 'User Level', 'Approval Required', 'Limit', 'Notes']
    
    def get_column_widths(self):
        return [25, 15, 15, 15, 30]
    
    def get_data(self):
        # Static authorization matrix - would be configurable in real implementation
        return [
            {'Action': 'Create Sale', 'User Level': 'Sales Rep', 'Approval Required': 'No', 'Limit': 'Unlimited', 'Notes': 'Standard sales'},
            {'Action': 'Apply Discount (0-5%)', 'User Level': 'Sales Rep', 'Approval Required': 'No', 'Limit': '5%', 'Notes': 'Auto-approved'},
            {'Action': 'Apply Discount (5-10%)', 'User Level': 'Sales Manager', 'Approval Required': 'Yes', 'Limit': '10%', 'Notes': 'Manager approval'},
            {'Action': 'Apply Discount (>10%)', 'User Level': 'Director', 'Approval Required': 'Yes', 'Limit': 'Unlimited', 'Notes': 'Director approval'},
            {'Action': 'Cancel Sale', 'User Level': 'Sales Manager', 'Approval Required': 'Yes', 'Limit': '-', 'Notes': 'With documentation'},
            {'Action': 'Modify Payment Plan', 'User Level': 'Finance', 'Approval Required': 'Yes', 'Limit': '-', 'Notes': 'Finance approval'},
            {'Action': 'Refund Payment', 'User Level': 'Finance Manager', 'Approval Required': 'Yes', 'Limit': '-', 'Notes': 'With documentation'},
            {'Action': 'Delete Record', 'User Level': 'Admin', 'Approval Required': 'Yes', 'Limit': '-', 'Notes': 'Audit trail required'},
        ]


class SalesExchangeRateReport(BaseReportData):
    """17. Sales Status Report (Exchange Rate Difference)"""
    
    def get_title(self):
        return "Sales Exchange Rate Analysis"
    
    def get_headers(self):
        return ['Contract', 'Customer', 'Currency', 'Original Amount', 'Current Rate', 'Current Value', 'FX Gain/Loss']
    
    def get_column_widths(self):
        return [15, 20, 12, 18, 15, 18, 18]
    
    def get_data(self):
        sales = self.env['propertio.sale'].search(self.secure_domain('propertio.sale'))
        data = []
        
        for sale in sales:
            currency = sale.currency_id.name if sale.currency_id else 'USD'
            original = sale.total_amount or 0
            # Would need actual exchange rate tracking
            current_rate = 1.0
            current_value = original * current_rate
            fx_diff = current_value - original
            
            data.append({
                'Contract': sale.name or '',
                'Customer': sale.partner_id.name or '',
                'Currency': currency,
                'Original Amount': original,
                'Current Rate': current_rate,
                'Current Value': current_value,
                'FX Gain/Loss': fx_diff
            })
        
        return data


class DailyCashRegisterReport(BaseReportData):
    """18. Daily Cash Register Report"""
    
    def get_title(self):
        return "Daily Cash Register Report"
    
    def get_headers(self):
        return ['Time', 'Transaction', 'Customer', 'Type', 'Amount', 'Running Total', 'Cashier']
    
    def get_column_widths(self):
        return [12, 15, 20, 12, 15, 18, 15]
    
    def get_data(self):
        report_date = self.date_from or date.today()
        
        payments = self.env['propertio.payment'].search(
            self.secure_domain('propertio.payment', [('payment_date', '=', report_date)]),
            order='create_date'
        )
        
        data = []
        running_total = 0
        
        for payment in payments:
            running_total += payment.amount or 0
            data.append({
                'Time': payment.create_date.strftime('%H:%M') if payment.create_date else '',
                'Transaction': payment.name or '',
                'Customer': payment.partner_id.name or '',
                'Type': 'Receipt',
                'Amount': payment.amount or 0,
                'Running Total': running_total,
                'Cashier': payment.create_uid.name if payment.create_uid else ''
            })
        
        return data
    
    def get_summary(self):
        data = self.get_data()
        return {
            'Total Transactions': len(data),
            'Total Amount': sum(d['Amount'] for d in data),
            'Report Date': str(self.date_from or date.today())
        }


class CRMLogRecordsReport(BaseReportData):
    """19. CRM Log Records"""
    
    def get_title(self):
        return "CRM Activity Log"
    
    def get_headers(self):
        return ['Date/Time', 'User', 'Action', 'Record', 'Details', 'IP Address']
    
    def get_column_widths(self):
        return [18, 15, 15, 20, 30, 15]
    
    def get_data(self):
        # Would integrate with mail.message or audit log
        domain = [('model', 'in', ['propertio.sale', 'propertio.payment', 'propertio.unit'])]
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        
        messages = self.env['mail.message'].search(self.secure_domain('mail.message', domain), order='date desc', limit=500)
        data = []
        
        for msg in messages:
            data.append({
                'Date/Time': msg.date.strftime('%Y-%m-%d %H:%M') if msg.date else '',
                'User': msg.author_id.name if msg.author_id else 'System',
                'Action': msg.message_type or '',
                'Record': f"{msg.model}/{msg.res_id}" if msg.model else '',
                'Details': (msg.body or '')[:100],
                'IP Address': '-'
            })
        
        return data[:200]


class CustomerJourneyIndividualReport(BaseReportData):
    """20. Customer Journey Report (Individual Based)"""
    
    def get_title(self):
        return "Individual Customer Journey"
    
    def get_headers(self):
        return ['Date', 'Event', 'Type', 'Value', 'Status', 'Handled By', 'Notes']
    
    def get_column_widths(self):
        return [12, 20, 15, 15, 12, 15, 25]
    
    def get_data(self):
        partner_id = self.options.get('partner_id')
        if not partner_id:
            return []
        
        partner = self.env['res.partner'].browse(partner_id)
        sales = self.env['propertio.sale'].search(self.secure_domain('propertio.sale', [('partner_id', '=', partner_id)]))
        payments = self.env['propertio.payment'].search(self.secure_domain('propertio.payment', [('partner_id', '=', partner_id)]))
        
        data = []
        
        # Add sales events
        for sale in sales:
            data.append({
                'Date': self.format_date(sale.date_order),
                'Event': f"Sale: {sale.name}",
                'Type': 'Sale',
                'Value': sale.total_amount or 0,
                'Status': sale.state.title() if sale.state else '',
                'Handled By': sale.user_id.name if sale.user_id else '',
                'Notes': sale.unit_id.name if sale.unit_id else ''
            })
        
        # Add payment events
        for payment in payments:
            data.append({
                'Date': self.format_date(payment.payment_date),
                'Event': f"Payment: {payment.name}",
                'Type': 'Payment',
                'Value': payment.amount or 0,
                'Status': 'Completed',
                'Handled By': payment.create_uid.name if payment.create_uid else '',
                'Notes': payment.reference or ''
            })
        
        return sorted(data, key=lambda x: x['Date'], reverse=True)


class TitleDeedInvoiceReport(BaseReportData):
    """21. Title Deed & Invoice Report"""
    
    def get_title(self):
        return "Title Deed & Invoice Status"
    
    def get_headers(self):
        return ['Contract', 'Customer', 'Unit', 'Sale Value', 'Title Deed Status', 'Invoice Status', 'Notes']
    
    def get_column_widths(self):
        return [15, 20, 15, 15, 18, 15, 20]
    
    def get_data(self):
        sales = self.env['propertio.sale'].search(self.secure_domain('propertio.sale', [('state', '=', 'sale')]))
        data = []
        
        for sale in sales:
            paid = sum(sale.installment_ids.filtered(lambda x: x.is_paid).mapped('amount'))
            total = sale.total_amount or 0
            
            # Title deed status based on payment completion
            if paid >= total:
                deed_status = 'Ready for Transfer'
            elif paid >= total * 0.5:
                deed_status = 'Pending (50%+ Paid)'
            else:
                deed_status = 'Not Ready'
            
            data.append({
                'Contract': sale.name or '',
                'Customer': sale.partner_id.name or '',
                'Unit': sale.unit_id.name if sale.unit_id else '',
                'Sale Value': total,
                'Title Deed Status': deed_status,
                'Invoice Status': 'Issued' if sale.state == 'sale' else 'Pending',
                'Notes': ''
            })
        
        return data


class IndependentUnitsReport(BaseReportData):
    """22. Independent Units Report"""
    
    def get_title(self):
        return "Independent Units Report"
    
    def get_headers(self):
        return ['Unit Code', 'Type', 'Location', 'Area (sqm)', 'List Price', 'Status', 'Notes']
    
    def get_column_widths(self):
        return [15, 15, 20, 12, 18, 12, 20]
    
    def get_data(self):
        # All Independent Units
        domain = []
        if self.project_id:
            domain.append(('project_id', '=', self.project_id.id))
        units = self.env['propertio.unit'].search(self.secure_domain('propertio.unit', domain))
        data = []
        
        for unit in units:
            data.append({
                'Unit Code': unit.name or '',
                'Type': unit.category_id.name if unit.category_id else '',
                'Location': unit.address or '',
                'Area (sqm)': unit.area or 0,
                'List Price': unit.list_price or 0,
                'Status': unit.state.title() if unit.state else '',
                'Notes': ''
            })
        
        return data


class ConstructionProgressReport(BaseReportData):
    """23. Project-Based Construction Progress Report"""
    
    def get_title(self):
        return "Construction Progress Report"
    
    def get_headers(self):
        return ['Project', 'Total Units', 'Sold', 'Construction %', 'Expected Completion', 'Sales Value', 'Collected']
    
    def get_column_widths(self):
        return [20, 12, 12, 15, 18, 18, 18]
    
    def get_data(self):
        projects = self.env['propertio.project'].search(self.secure_domain('propertio.project'))
        data = []
        
        for project in projects:
            units = self.env['propertio.unit'].search(self.secure_domain('propertio.unit', [('project_id', '=', project.id)]))
            sold_units = units.filtered(lambda u: u.state == 'sold')

            sales = self.env['propertio.sale'].search(self.secure_domain('propertio.sale', [('unit_id', 'in', units.ids)]))
            total_sales = sum(s.total_amount or 0 for s in sales)
            collected = sum(s.installment_ids.filtered(lambda x: x.is_paid).mapped('amount') for s in sales)
            
            data.append({
                'Project': project.name or '',
                'Total Units': len(units),
                'Sold': len(sold_units),
                'Construction %': f"{project.construction_progress or 0:.0f}%" if hasattr(project, 'construction_progress') else '-',
                'Expected Completion': self.format_date(project.completion_date) if hasattr(project, 'completion_date') else '-',
                'Sales Value': total_sales,
                'Collected': collected
            })
        
        return data


class WebFormTrackingReport(BaseReportData):
    """24. Web Form Tracking Report"""
    
    def get_title(self):
        return "Web Form Lead Tracking"
    
    def get_headers(self):
        return ['Date', 'Form Source', 'Lead Count', 'Qualified', 'Converted', 'Conversion Rate']
    
    def get_column_widths(self):
        return [12, 20, 12, 12, 12, 15]
    
    def get_data(self):
        # Placeholder - would integrate with website/CRM
        return [
            {'Date': self.format_date(date.today()), 'Form Source': 'Website Contact', 'Lead Count': 0, 'Qualified': 0, 'Converted': 0, 'Conversion Rate': '0%'},
            {'Date': self.format_date(date.today()), 'Form Source': 'Landing Page', 'Lead Count': 0, 'Qualified': 0, 'Converted': 0, 'Conversion Rate': '0%'},
        ]


class CustomerOverallStatusReport(BaseReportData):
    """25. Customer Overall Status Report"""
    
    def get_title(self):
        return "Customer Overall Status"
    
    def get_headers(self):
        return ['Customer', 'Total Purchases', 'Total Value', 'Paid', 'Outstanding', 'Risk Level', 'Last Activity']
    
    def get_column_widths(self):
        return [20, 15, 18, 18, 18, 12, 15]
    
    def get_data(self):
        partners = self.env['res.partner'].search(self.secure_domain('res.partner'))
        data = []
        
        for partner in partners:
            sales = self.env['propertio.sale'].search(self.secure_domain('propertio.sale', [('partner_id', '=', partner.id)]))
            if not sales:
                continue
            
            total_value = sum(s.total_amount or 0 for s in sales)
            paid = sum(sum(s.installment_ids.filtered(lambda x: x.is_paid).mapped('amount')) for s in sales)
            outstanding = total_value - paid
            
            # Risk level based on overdue payments
            overdue = sum(1 for s in sales for i in s.installment_ids if i.payment_status == 'overdue')
            risk = 'High' if overdue > 2 else ('Medium' if overdue > 0 else 'Low')
            
            last_payment = self.env['propertio.payment'].search(
                self.secure_domain('propertio.payment', [('partner_id', '=', partner.id)]),
                order='payment_date desc',
                limit=1
            )
            
            data.append({
                'Customer': partner.name,
                'Total Purchases': len(sales),
                'Total Value': total_value,
                'Paid': paid,
                'Outstanding': outstanding,
                'Risk Level': risk,
                'Last Activity': self.format_date(last_payment.payment_date) if last_payment else '-'
            })
        
        return sorted(data, key=lambda x: x['Outstanding'], reverse=True)


class PaymentPlanVATReport(BaseReportData):
    """26. Payment Plan Table (VAT Included)"""
    
    def get_title(self):
        return "Payment Plan (VAT Included)"
    
    def get_headers(self):
        return ['Contract', 'Customer', 'Installment', 'Due Date', 'Net Amount', 'VAT', 'Total', 'Status']
    
    def get_column_widths(self):
        return [15, 20, 15, 12, 15, 12, 15, 12]
    
    def get_data(self):
        VAT_RATE = 0.18  # 18% VAT - configurable
        
        domain = []
        if self.date_from:
            domain.append(('date_due', '>=', self.date_from))
        if self.date_to:
            domain.append(('date_due', '<=', self.date_to))
        
        installments = self.env['propertio.installment'].search(self.secure_domain('propertio.installment', domain), order='date_due')
        data = []
        
        for inst in installments:
            net = inst.amount or 0
            vat = net * VAT_RATE
            total = net + vat
            
            data.append({
                'Contract': inst.sale_id.name if inst.sale_id else '',
                'Customer': inst.partner_id.name or '',
                'Installment': inst.name or '',
                'Due Date': self.format_date(inst.date_due),
                'Net Amount': net,
                'VAT': vat,
                'Total': total,
                'Status': inst.payment_status.title() if inst.payment_status else '',
                '_status': inst.payment_status or ''
            })
        
        return data


class LeadReport(BaseReportData):
    """27. Lead Report"""
    
    def get_title(self):
        return "Lead Report"
    
    def get_headers(self):
        return ['Lead', 'Source', 'Date', 'Assigned To', 'Status', 'Value', 'Probability']
    
    def get_column_widths(self):
        return [20, 15, 12, 15, 12, 15, 12]
    
    def get_data(self):
        # Would integrate with CRM leads
        try:
            leads = self.env['crm.lead'].search(self.secure_domain('crm.lead'), limit=100)
            data = []
            
            for lead in leads:
                data.append({
                    'Lead': lead.name or '',
                    'Source': lead.source_id.name if lead.source_id else '',
                    'Date': self.format_date(lead.create_date),
                    'Assigned To': lead.user_id.name if lead.user_id else '',
                    'Status': lead.stage_id.name if lead.stage_id else '',
                    'Value': lead.expected_revenue or 0,
                    'Probability': f"{lead.probability or 0}%"
                })
            
            return data
        except:
            return []


class AdvertisingLeadsReport(BaseReportData):
    """28. Advertising Leads Report"""
    
    def get_title(self):
        return "Advertising Leads Report"
    
    def get_headers(self):
        return ['Campaign', 'Platform', 'Leads', 'Cost', 'Conversions', 'Revenue', 'ROI']
    
    def get_column_widths(self):
        return [20, 15, 12, 15, 12, 15, 12]
    
    def get_data(self):
        # Placeholder - would integrate with marketing automation
        return [
            {'Campaign': 'Google Ads Q1', 'Platform': 'Google', 'Leads': 0, 'Cost': 0, 'Conversions': 0, 'Revenue': 0, 'ROI': '0%'},
            {'Campaign': 'Facebook Spring', 'Platform': 'Meta', 'Leads': 0, 'Cost': 0, 'Conversions': 0, 'Revenue': 0, 'ROI': '0%'},
        ]


class CommissionReport(BaseReportData):
    """29. Müşteri Prim Raporu - Commission per salesperson"""

    def get_title(self):
        return "Commission Report (Müşteri Prim Raporu)"

    def get_headers(self):
        return ['Salesperson', 'Period', 'Sales Count', 'Total Revenue', 'Gross Commission', 'Deductions', 'Net Commission']

    def get_column_widths(self):
        return [20, 12, 12, 18, 18, 15, 18]

    def get_data(self):
        try:
            comms = self.env['propertio.commission'].search(self.secure_domain('propertio.commission'), order='period_from desc', limit=100)
            out = []
            for c in comms:
                sales = self.env['propertio.sale'].search(self.secure_domain('propertio.sale', [
                    ('sales_person_id', '=', c.user_id.id),
                    ('state', '=', 'confirmed'),
                    ('date_sale', '>=', c.period_from),
                    ('date_sale', '<=', c.period_to),
                ]))
                out.append({
                    'Salesperson': c.user_id.name,
                    'Period': '%s - %s' % (c.period_from, c.period_to),
                    'Sales Count': len(sales),
                    'Total Revenue': sum(sales.mapped('sale_price')),
                    'Gross Commission': c.gross_commission or 0,
                    'Deductions': c.deductions or 0,
                    'Net Commission': c.net_commission or 0,
                })
            return out
        except Exception:
            return []


class TapuStatusReport(BaseReportData):
    """30. Tapu Durum Raporu"""

    def get_title(self):
        return "Title Deed Status Report (Tapu Durum Raporu)"

    def get_headers(self):
        return ['Sale', 'Customer', 'Unit', 'Tapu No', 'Tapu Date', 'State', 'Appointment']

    def get_column_widths(self):
        return [15, 20, 12, 15, 12, 12, 18]

    def get_data(self):
        try:
            deeds = self.env['propertio.title.deed'].search(self.secure_domain('propertio.title.deed'))
            return [{
                'Sale': d.sale_id.name,
                'Customer': d.partner_id.name,
                'Unit': d.unit_id.name,
                'Tapu No': d.tapu_no or '',
                'Tapu Date': self.format_date(d.tapu_date),
                'State': d.state or '',
                'Appointment': str(d.tapu_appointment) if d.tapu_appointment else '',
            } for d in deeds]
        except Exception:
            return []


class HandoverStatusReport(BaseReportData):
    """31. Teslim Durumu Raporu"""

    def get_title(self):
        return "Handover Status Report (Teslim Durumu)"

    def get_headers(self):
        return ['Reference', 'Sale', 'Customer', 'Handover Date', 'State', 'Payment Complete', 'Keys Handed']

    def get_column_widths(self):
        return [12, 15, 20, 12, 12, 12, 12]

    def get_data(self):
        try:
            handovers = self.env['propertio.handover'].search(self.secure_domain('propertio.handover'))
            return [{
                'Reference': h.name,
                'Sale': h.sale_id.name,
                'Customer': h.partner_id.name,
                'Handover Date': self.format_date(h.handover_date),
                'State': h.state or '',
                'Payment Complete': 'Yes' if h.payment_complete else 'No',
                'Keys Handed': 'Yes' if h.keys_handed else 'No',
            } for h in handovers]
        except Exception:
            return []


class VATSummaryReport(BaseReportData):
    """32. KDV Özet Raporu"""

    def get_title(self):
        return "VAT Summary Report (KDV Özet)"

    def get_headers(self):
        return ['Period', 'Net Amount', 'VAT 20%', 'Gross Amount']

    def get_column_widths(self):
        return [15, 18, 15, 18]

    def get_data(self):
        payments = self.env['propertio.payment'].search(self.secure_domain('propertio.payment', [('state', '=', 'posted')]))
        by_month = {}
        for p in payments:
            key = p.payment_date.strftime('%Y-%m') if hasattr(p.payment_date, 'strftime') else str(p.payment_date)[:7]
            if key not in by_month:
                by_month[key] = {'net': 0, 'vat': 0, 'gross': 0}
            net = p.amount / 1.2 if getattr(p, 'vat_rate', 20) else p.amount / 1.2
            vat = p.amount - net
            by_month[key]['net'] += net
            by_month[key]['vat'] += vat
            by_month[key]['gross'] += p.amount
        return [{'Period': k, 'Net Amount': v['net'], 'VAT 20%': v['vat'], 'Gross Amount': v['gross']} for k, v in sorted(by_month.items())]


class CashRegisterSummaryReport(BaseReportData):
    """33. Kasa Özeti"""

    def get_title(self):
        return "Cash Register Summary (Kasa Özeti)"

    def get_headers(self):
        return ['Register', 'Currency', 'Opening', 'Current Balance', 'Responsible']

    def get_column_widths(self):
        return [15, 10, 18, 18, 15]

    def get_data(self):
        try:
            regs = self.env['propertio.cash.register'].search(self.secure_domain('propertio.cash.register'))
            return [{
                'Register': r.name,
                'Currency': r.currency_id.name,
                'Opening': r.opening_balance or 0,
                'Current Balance': r.current_balance or 0,
                'Responsible': r.responsible_id.name or '',
            } for r in regs]
        except Exception:
            return []


class CustomerSegmentationReport(BaseReportData):
    """34. Müşteri Segmentasyon"""

    def get_title(self):
        return "Customer Segmentation Report"

    def get_headers(self):
        return ['Customer', 'Nationality', 'Lead Source', 'Budget Min', 'Budget Max', 'Total Purchased', 'Risk Level']

    def get_column_widths(self):
        return [20, 12, 15, 15, 15, 18, 12]

    def get_data(self):
        try:
            partners = self.env['res.partner'].search(self.secure_domain('res.partner', [('total_purchased_value', '>', 0)]))
            return [{
                'Customer': p.name,
                'Nationality': p.nationality.name if getattr(p, 'nationality', None) and p.nationality else '',
                'Lead Source': getattr(p, 'lead_source', '') or '',
                'Budget Min': getattr(p, 'budget_min', 0) or 0,
                'Budget Max': getattr(p, 'budget_max', 0) or 0,
                'Total Purchased': getattr(p, 'total_purchased_value', 0) or 0,
                'Risk Level': getattr(p, 'risk_level', '') or '',
            } for p in partners[:200]]
        except Exception:
            return []


class ProjectProfitabilityReport(BaseReportData):
    """35. Proje Karlılık Analizi"""

    def get_title(self):
        return "Project Profitability Analysis"

    def get_headers(self):
        return ['Project', 'Total Units', 'Sold', 'Total GDV', 'Sold Value', 'Collected', 'Collection %']

    def get_column_widths(self):
        return [20, 12, 10, 18, 18, 18, 12]

    def get_data(self):
        projects = self.env['propertio.project'].search(self.secure_domain('propertio.project'))
        data = []
        for p in projects:
            units = self.env['propertio.unit'].search(self.secure_domain('propertio.unit', [('project_id', '=', p.id)]))
            sold = units.filtered(lambda u: u.state == 'sold')
            sold_value = sum(sold.mapped('sold_value'))
            collected = sum(sold.mapped('collected_amount'))
            data.append({
                'Project': p.name,
                'Total Units': len(units),
                'Sold': len(sold),
                'Total GDV': p.gdv or 0,
                'Sold Value': sold_value,
                'Collected': collected,
                'Collection %': '%.1f' % (collected / sold_value * 100) if sold_value else '0',
            })
        return data


class CommunicationReport(BaseReportData):
    """36. İletişim Raporu"""

    def get_title(self):
        return "Communication Report (İletişim Raporu)"

    def get_headers(self):
        return ['Date', 'Model', 'Record', 'Author', 'Body Preview']

    def get_column_widths(self):
        return [18, 20, 12, 15, 40]

    def get_data(self):
        try:
            messages = self.env['mail.message'].search(
                self.secure_domain('mail.message', [('model', 'in', ['propertio.sale', 'propertio.payment', 'propertio.unit', 'res.partner'])]),
                order='date desc',
                limit=300
            )
            return [{
                'Date': m.date.strftime('%Y-%m-%d %H:%M') if m.date else '',
                'Model': m.model or '',
                'Record': str(m.res_id),
                'Author': m.author_id.name if m.author_id else 'System',
                'Body Preview': (m.body or '')[:80].replace('\n', ' '),
            } for m in messages]
        except Exception:
            return []


# Report registry
REPORT_REGISTRY = {
    'sales_collection_summary': SalesCollectionSummaryReport,
    'type_based_sales': TypeBasedSalesReport,
    'customer_journey': CustomerJourneyReport,
    'sales_report': SalesReport,
    'cash_register': CashRegisterReport,
    'approval_based_sales': ApprovalBasedSalesChart,
    'total_sales_chart': TotalSalesChartReport,
    'incoming_payments_chart': IncomingPaymentsChartReport,
    'end_of_day_meeting': EndOfDayMeetingReport,
    'daily_sales_quantity': DailySalesQuantityReport,
    'cash_flow_statement': CashFlowStatementReport,
    'employee_performance': EmployeePerformanceReport,
    'sales_status': SalesStatusReport,
    'payment_plan_table': PaymentPlanTableReport,
    'expected_payment_list': ExpectedPaymentListReport,
    'authorization_matrix': AuthorizationMatrixReport,
    'sales_exchange_rate': SalesExchangeRateReport,
    'daily_cash_register': DailyCashRegisterReport,
    'crm_log_records': CRMLogRecordsReport,
    'customer_journey_individual': CustomerJourneyIndividualReport,
    'title_deed_invoice': TitleDeedInvoiceReport,
    'independent_units': IndependentUnitsReport,
    'construction_progress': ConstructionProgressReport,
    'web_form_tracking': WebFormTrackingReport,
    'customer_overall_status': CustomerOverallStatusReport,
    'payment_plan_vat': PaymentPlanVATReport,
    'lead_report': LeadReport,
    'advertising_leads': AdvertisingLeadsReport,
    'commission_report': CommissionReport,
    'tapu_status': TapuStatusReport,
    'handover_status': HandoverStatusReport,
    'vat_summary': VATSummaryReport,
    'cash_register_summary': CashRegisterSummaryReport,
    'customer_segmentation': CustomerSegmentationReport,
    'project_profitability': ProjectProfitabilityReport,
    'communication_report': CommunicationReport,
}
