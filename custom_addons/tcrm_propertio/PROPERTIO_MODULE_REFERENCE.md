# Propertio Module — Complete Reference

**Module:** Propertio (Real Estate) · **Version:** 1.1  
**Summary:** The TCRM Real Estate Engine — inventory, sales, payment plans, collections, and 28+ reports with XLSX/CSV/PDF/HTML export.

---

## 1. Module Overview

- **Depends:** `base`, `web`, `mail`, `crm`, `tcrm_vector_sync`
- **External Python:** `xlsxwriter`, `reportlab`
- **Application:** Yes (main app icon in menu)

---

## 2. Menu & Window Structure

### 2.1 Root: **Propertio**

| Section        | Menu path                         | Description |
|----------------|-----------------------------------|-------------|
| **Inventory**  | Propertio → Inventory             | Projects, Units |
| **Sales**      | Propertio → Sales                 | New Sale wizard, Sales Contracts |
| **Collections**| Propertio → Collections           | Payments, Collection Map, Tahsilat, Proje Nakit, Nakit Akışı, Danışman Karnesi, Kırmızı Alarm |
| **Reporting**  | Propertio → Reporting             | Reports Center, GDV, Cash Flow, all report menus |
| **Configuration** | Propertio → Configuration      | Master Data, Personnel & Partners |

---

### 2.2 Inventory

| Screen / Action              | Model / Type      | View modes / Notes |
|-----------------------------|-------------------|--------------------|
| **Projects**                | `propertio.project` | list, form |
| **Units**                   | `propertio.unit`  | list, form |

---

### 2.3 Sales

| Screen / Action              | Model / Type           | View modes / Notes |
|-----------------------------|------------------------|--------------------|
| **New Sale** (wizard)       | `propertio.sale.wizard` | form (dialog)   |
| **Sales Contracts**         | `propertio.sale`      | list, form; search view with filters (Draft/Confirmed) and group by State |

---

### 2.4 Collections

| Screen / Action              | Model / Type           | View modes / Notes |
|-----------------------------|------------------------|--------------------|
| **Payments**                | `propertio.payment`   | list, form |
| **Sales & Collection Map**  | `propertio.installment` | list, pivot, graph, form (color by status) |
| **Tahsilat ve Satış Durumu**| `propertio.installment` | list, form (Turkish labels) |
| **Proje Nakit Durumu**      | `propertio.installment` | pivot, graph, list |
| **Gelecek Nakit Akışı**     | `propertio.installment` | graph, pivot, list |
| **Danışman Karnesi**        | `propertio.installment` | pivot, graph, list |
| **Danışman Karnesi (Bu Ay)**| Server action         | Opens Danışman Karnesi filtered to this month |
| **Kırmızı Alarm Müşteriler**| `propertio.installment` | list, form (overdue ≥ 15 days) |

---

### 2.5 Reporting

| Screen / Action        | Model / Type                | View modes / Notes |
|------------------------|-----------------------------|--------------------|
| **Reports Center**      | —                           | Parent for all report menus |
| **Export Reports**      | `propertio.unified.report.wizard` | form (unified report launcher) |
| **Project GDV Analysis** | `propertio.unit`          | pivot, graph, list |
| **Cash Flow Forecast**  | `propertio.installment`     | graph, pivot, list |

All numbered reports below open the **Unified Report Wizard** (`propertio.unified.report.wizard`) with a default report type; user picks date range, filters, format (XLSX/CSV/PDF/HTML), then Generate / Download / View in Browser.

---

### 2.6 Configuration

**Master Data** (under Configuration):

| Screen             | Model                     | View modes |
|--------------------|---------------------------|------------|
| Unit Features      | `propertio.feature`       | list, form (icon, name, color) |
| Project Types      | `propertio.project.type`  | list, form (name, active, properties_definition) |
| Project Stages     | `propertio.project.stage` | list, form |
| Property Categories| `propertio.unit.category` | list, form (name, active, properties_definition) |
| Detailed Statuses | `propertio.unit.status`   | list, form |
| Sale Stages        | `propertio.sale.stage`    | list, form |

**Personnel & Partners:**

| Screen          | Model        | Domain / Notes |
|-----------------|-------------|----------------|
| Agencies        | `res.partner` | `is_company = True` |
| Sales Personnel | `res.users`  | list, form |

---

## 3. Every Screen (Views) in Detail

### 3.1 Projects (`propertio.project`)

- **Form:** Title (name), city, type, stage, GDV, unit count, properties; notebook: Amenities & Features (standard/extra), Units Inventory (inline list), Blocks (inline list).
- **List:** name, city, type, stage, unit_count, gdv (sum).

### 3.2 Units (`propertio.unit`)

- **Form:** Statusbar (available / option / sold / handover); button **Sales History**; name, project, block, floor, entrance, category, status, view_type, list_price, gross_m2, properties; notebook: General Info, Features, Financial Stats, Documents.
- **List:** project, block, name, floor, category, status, gross_m2, list_price, state (badge).

### 3.3 Sales Contracts (`propertio.sale`)

- **Form:** Header: **Confirm Sale**, **Print / Export**; statusbar draft / confirmed / cancel. Stat buttons: Property, Customer, Payments, Collections. Contract ref, contract_no, partner, unit, date_sale, sale_price, total_paid, balance. Notebook: Payment Plan (installments + Rebalance), General Info, Unit Specs, Legal & Bank, Team, Technical Financials.
- **List:** name, project, partner, unit, sale_price (sum), state (badge). Header: **Download Word** (batch).
- **Search:** name, partner, unit, project; filters Draft/Confirmed; group by State.

### 3.4 Payments (`propertio.payment`)

- **Form:** Post / Cancel; name, partner, sale, payment_method, payment_date, currency, amount, exchange_rate, covered_amount; chatter.
- **List:** name, payment_date, partner, sale, amount, currency, state.

### 3.5 Installment / Collection views (`propertio.installment`)

- **Collection Map (list):** sale, partner, name, date_due, amount, amount_paid, residual, payment_status, type (color by status).
- **Tahsilat ve Satış Durumu (list):** Same idea, Turkish column labels.
- **Proje Nakit (pivot/graph):** By project and date; measures: total value, tahsilat, kalan.
- **Nakit Akışı (graph/pivot):** Expected by due date vs actual by payment date.
- **Danışman Karnesi (pivot/graph):** By sales person, measure: amount_paid.
- **Kırmızı Alarm (list):** partner, sale, project, name, date_due, overdue_days, residual, amount, payment_status, sales_person_id; domain overdue_days ≥ 15.

### 3.6 Wizards

- **Print / Export** (`propertio.print.options`): Buttons: Download PDF, Download Word, View HTML, Batch Word (linked from sale form).
- **New Sale** (`propertio.sale.wizard`): Partner, unit, currency, price, list_price; Payment Terms (down_payment, installments, balloon); Exchange rates (TCMB); **Generate Sale**.
- **Unified Report** (`propertio.unified.report.wizard`): Report type, export format, date range, filters (project, partner, user); Generate, Download, View in Browser, New Report.
- **Export Reports** (alternative entry): `propertio.report.export` — report_type, export_format, date_from/date_to; Export, Download.

### 3.7 CRM Lead (inherited)

- **Form & Kanban:** 5-star priority widget on `crm.lead`.

---

## 4. Every Report (28 Report Types + 2 QWeb PDFs)

### 4.1 QWeb PDF Reports (Print from list/form)

| Report name        | Binding model     | Template / Purpose |
|--------------------|-------------------|---------------------|
| **Sales Contract** | `propertio.sale`  | `report_contract_document` — buyer, date, project, unit, property table, financial terms, payment plan, signatures. |
| **Collection Report** | `propertio.installment` | `report_collection_doc` — Sale ref, description, due date, amount, paid, residual, status (color by payment_status). |

### 4.2 Unified Report Wizard (28 types) — export: XLSX, CSV, PDF, HTML

**Collection & Payments**

1. **Sales Collection Summary** — Contract, customer, unit, sale value, collected, outstanding, collection %, payment status.  
2. **Payment Plan Table** — Contract, customer, installment, due date, amount, paid, balance, status.  
3. **Expected Payment List** — Due date, days until due, contract, customer, installment, amount due, status.  
4. **Payment Plan (VAT Included)** — Same as 14 with Net, VAT, Total.  
5. **Incoming & Expected Payments** — Month, expected, received, variance, collection rate.  
+ **Tahsilat ve Satış Durumu**, **Proje Nakit Durumu**, **Gelecek Nakit Akışı**, **Kırmızı Alarm Müşteriler** (also under Collections as live views).

**Sales Reports**

6. **Sales Report** — Contract, date, customer, project, unit, sale price, discount, net amount, status.  
7. **Type-Based Sales & Inventory** — Unit type, total/available/reserved/sold units, stock value, sold value, available value.  
8. **Approval-Based Sales Chart** — Status, count, total value, avg value, percentage.  
9. **Total Sales Chart** — Period, sales count, total value, avg value, growth %.  
10. **Daily Sales Quantity** — Date, day, units sold, total value, avg unit price.  
11. **Sales Status Report** — Contract, customer, unit, sale date, amount, paid, balance, status.  
12. **Sales Exchange Rate** — Contract, customer, currency, original amount, current rate, current value, FX gain/loss.

**Customer Reports**

13. **Customer Journey** — Customer, first contact, lead source, visits, offers, sales, total value, status.  
14. **Individual Customer Journey** — Date, event, type, value, status, handled by, notes (per partner).  
15. **Customer Overall Status** — Customer, total purchases, total value, paid, outstanding, risk level, last activity.

**Financial Reports**

16. **Cash Register Report** — Date, receipt #, customer, contract, amount, payment method, register, reference.  
17. **Daily Cash Register** — Time, transaction, customer, type, amount, running total, cashier.  
18. **Cash Flow Statement** — Period, opening balance, cash inflows, outflows, net flow, closing balance.

**Performance Reports**

19. **Employee Performance** — Salesperson, deals, total revenue, avg deal size, collection amount, collection rate, rank.  
20. **End-of-Day Meeting** — Date, salesperson, new leads, meetings, follow-ups, sales made, sales value.

**Property Reports**

21. **Independent Units** — Unit code, type, location, area, list price, status (units without project).  
22. **Construction Progress** — Project, total units, sold, construction %, expected completion, sales value, collected.  
23. **Title Deed & Invoice** — Contract, customer, unit, sale value, title deed status, invoice status, notes.

**Admin & Compliance**

24. **Authorization Matrix** — Action, user level, approval required, limit, notes (static matrix).  
25. **CRM Activity Log** — Date/time, user, action, record, details, IP (mail.message based).

**Marketing & Leads**

26. **Lead Report** — Lead, source, date, assigned to, status, value, probability.  
27. **Advertising Leads** — Campaign, platform, leads, cost, conversions, revenue, ROI.  
28. **Web Form Tracking** — Date, form source, lead count, qualified, converted, conversion rate.

---

## 5. Every Function (Actions & API)

### 5.1 Server actions (from UI)

| Name                      | Model             | Effect |
|---------------------------|-------------------|--------|
| **Export Contracts (Word)** | `propertio.sale` | Calls `records.action_export_batch_word()`. |
| **Danışman Karnesi (Bu Ay)** | `propertio.installment` | Calls `env['propertio.installment'].action_open_danisman_karnesi_this_month()`. |

### 5.2 Sale (`propertio.sale`)

| Method | Purpose |
|--------|---------|
| `action_rebalance_plan()` | Auto-balance payment plan / add remainder installment. |
| `action_confirm()` | Set state confirmed, unit state sold. |
| `action_view_installments()` | Open installments (list/graph/pivot). |
| `action_view_unit()` | Open unit form. |
| `action_view_customer()` | Open partner form. |
| `action_view_payments()` | Open payments list for this sale. |
| `action_download_word()` | act_url → `/propertio/contract_word/{id}`. |
| `action_print_contract_html()` | act_url to contract report HTML. |
| `action_export_batch_word()` | act_url batch Word (used by server action). |
| `action_download_pdf()` | act_url → `/propertio/contract_pdf/{id}`. |
| `action_open_full_screen()` | Open sale form. |
| `action_open_danisman_karnesi_this_month()` | Open Danışman Karnesi filtered to current month (called from server action on `propertio.installment`). |

### 5.3 Unit (`propertio.unit`)

| Method | Purpose |
|--------|---------|
| `action_view_sales_history()` | Open sales for this unit. |

### 5.4 Payment (`propertio.payment`)

| Method | Purpose |
|--------|---------|
| `action_post()` | Allocate payment to installments (FIFO), set state posted. |
| `action_cancel()` | Cancel payment. |

### 5.5 Wizards

| Wizard | Method | Purpose |
|--------|--------|---------|
| **Print options** | `action_download_pdf()` | Download contract PDF. |
| | `action_download_word()` | Download contract Word. |
| | `action_print_html()` | Open contract HTML. |
| | `action_export_word_batch()` | Batch Word export. |
| **Sale wizard** | `action_generate_sale()` | Create sale + installments from wizard. |
| **Unified report** | `action_generate_report()` | Generate report (XLSX/CSV/PDF/HTML). |
| | `action_download()` | Download generated file. |
| | `action_view_html()` | View HTML in browser. |
| | `action_print_pdf()` | Print as PDF. |
| | `action_reset()` | Reset wizard. |
| **Report export** | `action_export()` | Run export. |
| | `action_download()` | Download result. |

### 5.6 TCMB / Currency (`res.currency` — tcmb_manager)

| Method | Purpose |
|--------|---------|
| `get_tcmb_data(target_date=None)` | Fetch TCMB exchange rates. |
| `_apply_rates`, `_update_tcmb_rates` | Apply/update rates (cron). |

### 5.7 Controllers (HTTP)

| Route | Purpose |
|-------|---------|
| `/propertio/contract_word/<int:sale_id>` | Single contract Word download. |
| `/propertio/contract_word_batch` (POST, ids) | Batch contract Word. |
| `/propertio/contract_pdf/<int:sale_id>` | Contract PDF download. |

---

## 6. Data & Security

- **Data:** `data/propertio_data.xml` (default project types, stages, categories, etc.).
- **Security:** `security/ir.model.access.csv` — access rights for all Propertio models.
- **Templates:** `reports/contract_template.xml`, `reports/propertio_reports.xml` (QWeb), `reports/report_definitions.py` (28 report classes), `reports/report_generator.py` (XLSX/CSV/PDF/HTML build).

---

## 7. Summary Table

| Category | Count |
|----------|--------|
| **Menu sections** | 5 (Inventory, Sales, Collections, Reporting, Configuration) |
| **Window actions (screens)** | 20+ (projects, units, sales, payments, wizards, collection/installment views) |
| **Report types (unified wizard)** | 28 |
| **QWeb PDF reports** | 2 (Contract, Collection) |
| **Server actions** | 2 (Export Word, Danışman Bu Ay) |
| **Key model methods (actions)** | 20+ (sale, unit, payment, wizards, TCMB) |
| **Controllers** | 3 routes (Word single/batch, PDF) |

This document describes every window, screen, report, and main function of the **Propertio** module.
