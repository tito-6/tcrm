# -*- coding: utf-8 -*-
from datetime import date, datetime, time, timedelta

from tcrm import fields, http
from tcrm.http import request


class PropertioSearchController(http.Controller):
    def _secure_env(self):
        user = request.env.user
        company = user.company_id
        ctx = dict(request.env.context, allowed_company_ids=[company.id], force_company=company.id)
        return request.env["res.users"].with_context(ctx).env

    def _tenant_domain(self, model, domain=None):
        dom = list(domain or [])
        if "company_id" in model._fields:
            dom.append(("company_id", "=", request.env.user.company_id.id))
        return dom

    @http.route('/propertio/search', type='jsonrpc', auth='user')
    def search(self, q='', limit=10):
        """Global quick search: partners, units, sales, payments."""
        q = (q or '').strip()[:100]
        if not q:
            return {'partners': [], 'units': [], 'sales': [], 'payments': []}
        limit = min(int(limit), 20)
        out = {'partners': [], 'units': [], 'sales': [], 'payments': []}
        env = self._secure_env()
        Partner = env['res.partner']
        Unit = env['propertio.unit']
        Sale = env['propertio.sale']
        Payment = env['propertio.payment']
        partners = Partner.search(self._tenant_domain(Partner, [('name', 'ilike', q)]), limit=limit)
        for p in partners:
            out['partners'].append({'id': p.id, 'name': p.name, 'model': 'res.partner'})
        units = Unit.search(self._tenant_domain(Unit, ['|', ('name', 'ilike', q), ('unit_code', 'ilike', q)]), limit=limit)
        for u in units:
            out['units'].append({'id': u.id, 'name': u.name, 'model': 'propertio.unit'})
        sales = Sale.search(self._tenant_domain(Sale, [('name', 'ilike', q)]), limit=limit)
        for s in sales:
            out['sales'].append({'id': s.id, 'name': s.name, 'partner': s.partner_id.name, 'model': 'propertio.sale'})
        payments = Payment.search(self._tenant_domain(Payment, [('name', 'ilike', q)]), limit=limit)
        for p in payments:
            out['payments'].append({'id': p.id, 'name': p.name, 'partner': p.partner_id.name, 'model': 'propertio.payment'})
        return out


class PropertioDashboardController(http.Controller):
    def _secure_env(self):
        user = request.env.user
        company = user.company_id
        ctx = dict(request.env.context, allowed_company_ids=[company.id], force_company=company.id)
        return request.env["res.users"].with_context(ctx).env

    def _tenant_domain(self, model, domain=None):
        dom = list(domain or [])
        if "company_id" in model._fields:
            dom.append(("company_id", "=", request.env.user.company_id.id))
        return dom

    def _parse_period(self, date_from_raw=None, date_to_raw=None):
        """Default: first day of month → today when params omitted."""
        today = date.today()
        date_to = today
        date_from = today.replace(day=1)
        if date_to_raw:
            try:
                if isinstance(date_to_raw, str):
                    date_to = fields.Date.from_string(date_to_raw[:10])
                elif isinstance(date_to_raw, date):
                    date_to = date_to_raw
            except Exception:
                date_to = today
        if date_from_raw:
            try:
                if isinstance(date_from_raw, str):
                    date_from = fields.Date.from_string(date_from_raw[:10])
                elif isinstance(date_from_raw, date):
                    date_from = date_from_raw
            except Exception:
                date_from = date_to.replace(day=1)
        if date_from > date_to:
            date_from, date_to = date_to, date_from
        label = '%s → %s' % (date_from.isoformat(), date_to.isoformat())
        return date_from, date_to, label

    @http.route('/propertio/dashboard/data', type='jsonrpc', auth='user')
    def dashboard_data(self, date_from=None, date_to=None):
        """Return role-based dashboard data for the current user."""
        user = request.env.user
        role = user.propertio_role or 'sales'
        d0, d1, period_label = self._parse_period(date_from, date_to)

        if role == 'sales':
            return self._get_sales_dashboard_data(user, d0, d1, period_label)
        if role == 'collection':
            return self._get_collection_dashboard_data(user, d0, d1, period_label)
        if role == 'finance':
            return self._get_finance_dashboard_data(user, d0, d1, period_label)
        if role in ('manager', 'admin'):
            return self._get_manager_dashboard_data(user, d0, d1, period_label)
        if role == 'aftersales':
            return self._get_aftersales_dashboard_data(user, d0, d1, period_label)

        return self._get_sales_dashboard_data(user, d0, d1, period_label)

    def _get_sales_dashboard_data(self, user, period_start, period_end, period_label):
        today = date.today()
        month_start = period_start
        env = self._secure_env()
        Sale = env['propertio.sale']
        Unit = env['propertio.unit']

        my_sales = Sale.search(self._tenant_domain(Sale, [('sales_person_id', '=', user.id), ('state', '=', 'confirmed')]))
        this_month_sales = Sale.search(self._tenant_domain(Sale, [
            ('sales_person_id', '=', user.id),
            ('state', '=', 'confirmed'),
            ('date_sale', '>=', month_start.isoformat()),
            ('date_sale', '<=', period_end.isoformat()),
        ]))
        available_units = Unit.search_count(self._tenant_domain(Unit, [('state', '=', 'available')]))

        target_units = 5
        target_amount = 0
        ref_day = period_end if period_start <= today <= period_end else period_end
        try:
            Target = env['propertio.target']
            current = Target.search(self._tenant_domain(Target, [
                ('user_id', '=', user.id),
                ('date_from', '<=', ref_day),
                ('date_to', '>=', ref_day),
                ('state', '=', 'active'),
            ]), limit=1)
            if current:
                target_units = current.target_units or 5
                target_amount = current.target_amount or 0
        except Exception:
            pass

        achieved_pct = (len(this_month_sales) / target_units * 100) if target_units else 0
        end_month = (period_end.replace(day=28) + timedelta(days=4)).replace(day=1)
        remaining_days = max(0, (end_month - period_end).days)

        today_activities = []
        try:
            Activity = env['mail.activity']
            activities = Activity.search(self._tenant_domain(Activity, [
                ('user_id', '=', user.id),
                ('date_deadline', '>=', period_start.isoformat()),
                ('date_deadline', '<=', period_end.isoformat()),
                ('res_model', 'in', ['propertio.sale', 'crm.lead']),
            ]), limit=20)
            for act in activities:
                today_activities.append({
                    'id': act.id,
                    'res_model': act.res_model,
                    'res_id': act.res_id,
                    'summary': act.summary or '',
                    'note': (act.note or '')[:200],
                })
        except Exception:
            pass

        pipeline = []
        try:
            Lead = env['crm.lead']
            dt_start = datetime.combine(period_start, time.min)
            dt_end = datetime.combine(period_end, time.max)
            for stage in env['crm.stage'].search([], order='sequence'):
                count = Lead.search_count(self._tenant_domain(Lead, [
                    ('user_id', '=', user.id),
                    ('stage_id', '=', stage.id),
                    ('create_date', '>=', dt_start),
                    ('create_date', '<=', dt_end),
                ]))
                pipeline.append({'stage': stage.name, 'count': count})
        except Exception:
            pipeline = [{'stage': 'New', 'count': 0}]

        expiring_soon = 0

        return {
            'role': 'sales',
            'user_name': user.name,
            'date': today.isoformat(),
            'period_from': period_start.isoformat(),
            'period_to': period_end.isoformat(),
            'period_label': period_label,
            'my_sales_count': len(my_sales),
            'this_month_count': len(this_month_sales),
            'target_units': target_units,
            'target_amount': target_amount,
            'achieved_pct': round(achieved_pct, 1),
            'remaining_days': remaining_days,
            'available_units_count': available_units,
            'today_tasks': today_activities,
            'expiring_soon_count': expiring_soon,
            'pipeline': pipeline,
        }

    def _get_collection_dashboard_data(self, user, period_start, period_end, period_label):
        today = date.today()
        month_start = period_start
        env = self._secure_env()
        Installment = env['propertio.installment']
        Payment = env['propertio.payment']

        red_alerts = Installment.search(self._tenant_domain(Installment, [
            ('is_paid', '=', False),
            ('overdue_days', '>=', 15),
        ]))
        due_this_week_end = today + timedelta(days=7)
        due_this_week = Installment.search(self._tenant_domain(Installment, [
            ('is_paid', '=', False),
            ('date_due', '>=', today.isoformat()),
            ('date_due', '<=', due_this_week_end.isoformat()),
        ]))
        due_this_week_total = sum(due_this_week.mapped('residual'))

        today_calls = Installment.search(self._tenant_domain(Installment, [
            ('is_paid', '=', False),
            ('overdue_days', '>', 0),
        ]), order='overdue_days desc, residual desc', limit=15)
        call_list = []
        for inst in today_calls:
            call_list.append({
                'id': inst.id,
                'partner_id': inst.partner_id.id,
                'partner_name': inst.partner_id.name,
                'unit_name': inst.sale_id.unit_id.name if inst.sale_id and inst.sale_id.unit_id else '',
                'amount': inst.residual,
                'currency': inst.currency_id.name,
                'overdue_days': inst.overdue_days,
                'sale_id': inst.sale_id.id,
            })

        month_payments = Payment.search(self._tenant_domain(Payment, [
            ('state', '=', 'posted'),
            ('payment_date', '>=', month_start.isoformat()),
            ('payment_date', '<=', period_end.isoformat()),
        ]))
        collected_mtd = sum(month_payments.mapped('amount'))
        target_collection = 2000000
        ref_day = period_end if period_start <= today <= period_end else period_end
        try:
            Target = env['propertio.target']
            current = Target.search(self._tenant_domain(Target, [
                ('user_id', '=', user.id),
                ('date_from', '<=', ref_day),
                ('date_to', '>=', ref_day),
                ('state', '=', 'active'),
            ]), limit=1)
            if current:
                target_collection = current.target_collection or 2000000
        except Exception:
            pass
        collection_pct = (collected_mtd / target_collection * 100) if target_collection else 0
        remaining_month = target_collection - collected_mtd

        return {
            'role': 'collection',
            'user_name': user.name,
            'date': today.isoformat(),
            'period_from': period_start.isoformat(),
            'period_to': period_end.isoformat(),
            'period_label': period_label,
            'red_alerts_count': len(red_alerts),
            'due_this_week_count': len(due_this_week),
            'due_this_week_total': due_this_week_total,
            'today_calls': call_list,
            'target_collection': target_collection,
            'collected_mtd': collected_mtd,
            'collection_pct': round(collection_pct, 1),
            'remaining_this_month': max(0, remaining_month),
        }

    def _get_finance_dashboard_data(self, user, period_start, period_end, period_label):
        today = date.today()
        env = self._secure_env()
        Payment = env['propertio.payment']
        Installment = env['propertio.installment']

        payments_mtd = Payment.search(self._tenant_domain(Payment, [
            ('state', '=', 'posted'),
            ('payment_date', '>=', period_start.isoformat()),
            ('payment_date', '<=', period_end.isoformat()),
        ]))
        total_received = sum(payments_mtd.mapped('amount'))

        by_currency = {}
        for p in payments_mtd:
            c = p.currency_id.name
            if c not in by_currency:
                by_currency[c] = {'expected': 0, 'received': 0}
            by_currency[c]['received'] = by_currency[c].get('received', 0) + p.amount

        upcoming_end = today + timedelta(days=7)
        upcoming = Installment.search(self._tenant_domain(Installment, [
            ('is_paid', '=', False),
            ('date_due', '>=', today.isoformat()),
            ('date_due', '<=', upcoming_end.isoformat()),
        ]), order='date_due')
        upcoming_by_day = {}
        for inst in upcoming:
            d = inst.date_due.isoformat() if hasattr(inst.date_due, 'isoformat') else str(inst.date_due)
            if d not in upcoming_by_day:
                upcoming_by_day[d] = {'count': 0, 'amount': 0}
            upcoming_by_day[d]['count'] += 1
            upcoming_by_day[d]['amount'] += inst.residual

        return {
            'role': 'finance',
            'user_name': user.name,
            'date': today.isoformat(),
            'period_from': period_start.isoformat(),
            'period_to': period_end.isoformat(),
            'period_label': period_label,
            'total_received_mtd': total_received,
            'by_currency': by_currency,
            'upcoming_7_days': upcoming_by_day,
        }

    def _get_manager_dashboard_data(self, user, period_start, period_end, period_label):
        today = date.today()
        env = self._secure_env()
        Project = env['propertio.project']
        Unit = env['propertio.unit']
        Sale = env['propertio.sale']
        Installment = env['propertio.installment']
        Payment = env['propertio.payment']

        projects = Project.search(self._tenant_domain(Project))
        units = Unit.search(self._tenant_domain(Unit))
        sold_units = units.filtered(lambda u: u.state == 'sold')
        total_gdv = sum(projects.mapped('gdv')) or 0
        sold_value = sum(Unit.search(self._tenant_domain(Unit, [('state', '=', 'sold')])).mapped('sold_value')) or 0
        payments = Payment.search(self._tenant_domain(Payment, [
            ('state', '=', 'posted'),
            ('payment_date', '>=', period_start.isoformat()),
            ('payment_date', '<=', period_end.isoformat()),
        ]))
        collected = sum(payments.mapped('amount')) or 0

        this_month_sales = Sale.search(self._tenant_domain(Sale, [
            ('state', '=', 'confirmed'),
            ('date_sale', '>=', period_start.isoformat()),
            ('date_sale', '<=', period_end.isoformat()),
        ]))
        target_units = 20
        ref_day = period_end if period_start <= today <= period_end else period_end
        try:
            Target = env['propertio.target']
            current = Target.search(self._tenant_domain(Target, [
                ('date_from', '<=', ref_day),
                ('date_to', '>=', ref_day),
                ('state', '=', 'active'),
            ]), limit=1)
            if current:
                target_units = current.target_units or 20
        except Exception:
            pass

        top_salespersons = []
        try:
            for sale in this_month_sales:
                sp = sale.sales_person_id
                if not sp:
                    continue
                existing = next((x for x in top_salespersons if x['id'] == sp.id), None)
                if existing:
                    existing['count'] += 1
                    existing['value'] += sale.sale_price or 0
                else:
                    top_salespersons.append({
                        'id': sp.id,
                        'name': sp.name,
                        'count': 1,
                        'value': sale.sale_price or 0,
                    })
            top_salespersons.sort(key=lambda x: x['value'], reverse=True)
            top_salespersons = top_salespersons[:5]
        except Exception:
            pass

        installments = Installment.search(self._tenant_domain(Installment))
        on_time = len(installments.filtered(lambda i: i.payment_status == 'paid'))
        overdue_15 = len(installments.filtered(lambda i: i.overdue_days >= 15 and not i.is_paid))
        total_inst = len(installments)
        on_time_pct = (on_time / total_inst * 100) if total_inst else 0
        overdue_15_pct = (overdue_15 / total_inst * 100) if total_inst else 0

        project_progress = []
        for proj in projects[:10]:
            proj_units = Unit.search(self._tenant_domain(Unit, [('project_id', '=', proj.id)]))
            sold = len(proj_units.filtered(lambda u: u.state == 'sold'))
            total = len(proj_units)
            pct = (sold / total * 100) if total else 0
            project_progress.append({
                'name': proj.name,
                'sold': sold,
                'total': total,
                'pct': round(pct, 0),
            })

        return {
            'role': 'manager',
            'user_name': user.name,
            'date': today.isoformat(),
            'period_from': period_start.isoformat(),
            'period_to': period_end.isoformat(),
            'period_label': period_label,
            'projects_count': len(projects),
            'units_total': len(units),
            'units_sold': len(sold_units),
            'sold_pct': round(len(sold_units) / len(units) * 100, 0) if units else 0,
            'target_units': target_units,
            'actual_units_this_month': len(this_month_sales),
            'top_salespersons': top_salespersons,
            'on_time_pct': round(on_time_pct, 1),
            'overdue_15_pct': round(overdue_15_pct, 1),
            'total_gdv': total_gdv,
            'sold_value': sold_value,
            'collected_value': collected,
            'project_progress': project_progress,
        }

    def _get_aftersales_dashboard_data(self, user, period_start, period_end, period_label):
        today = date.today()
        return {
            'role': 'aftersales',
            'user_name': user.name,
            'date': today.isoformat(),
            'period_from': period_start.isoformat(),
            'period_to': period_end.isoformat(),
            'period_label': period_label,
            'tapu_appointments_this_week': 0,
        }
