import random
import datetime
from dateutil.relativedelta import relativedelta

print("Starting Demo Data Generation in Shell...")

# Env is available in shell context
Project = env['propertio.project']
Block = env['propertio.block']
Unit = env['propertio.unit']
Partner = env['res.partner']
Sale = env['propertio.sale']
Installment = env['propertio.installment']
Payment = env['propertio.payment']

# Master Data Generators
def get_or_create_master_data(model, name):
    record = env[model].search([('name', '=', name)], limit=1)
    if not record:
        record = env[model].create({'name': name})
    return record

type_resi = get_or_create_master_data('propertio.project.type', 'Residential Plus')
type_comm = get_or_create_master_data('propertio.project.type', 'Commercial Hub')

stage_plan = get_or_create_master_data('propertio.project.stage', 'Planning')
stage_const = get_or_create_master_data('propertio.project.stage', 'Under Construction')
stage_complete = get_or_create_master_data('propertio.project.stage', 'Completed')

cat_1 = get_or_create_master_data('propertio.unit.category', '1+1 Suite')
cat_2 = get_or_create_master_data('propertio.unit.category', '2+1 Family')
cat_duplex = get_or_create_master_data('propertio.unit.category', 'Roof Duplex')
cat_shop = get_or_create_master_data('propertio.unit.category', 'Street Shop')

status_avail = get_or_create_master_data('propertio.unit.status', 'Ready to Sell')
status_res = get_or_create_master_data('propertio.unit.status', 'Reserved')
status_sold = get_or_create_master_data('propertio.unit.status', 'Sold')

sale_stage_draft = get_or_create_master_data('propertio.sale.stage', 'Draft Contract')
sale_stage_signed = get_or_create_master_data('propertio.sale.stage', 'Signed')
sale_stage_legal = get_or_create_master_data('propertio.sale.stage', 'Legal Review')

def create_sale_logic(env, unit, partner, price, installments, start_date_str, currency, stage):
    Sale = env['propertio.sale']
    Installment = env['propertio.installment']
    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
    
    sale = Sale.create({
        'partner_id': partner.id,
        'unit_id': unit.id,
        'date_sale': start_date,
        'sale_price': price,
        'currency_id': currency.id,
        'state': 'confirmed',
        'stage_id': stage.id
    })
    unit.state = 'sold'
    unit.status_id = status_sold.id
    
    amount_per_install = price / installments
    for i in range(installments):
        date_due = start_date + relativedelta(months=i)
        Installment.create({
            'sale_id': sale.id,
            'name': f'{i+1}/{installments}',
            'date_due': date_due,
            'amount': amount_per_install,
            'type': 'installment'
        })
    return sale

def pay_sale_logic(env, sale, amount):
    Payment = env['propertio.payment']
    payment = Payment.create({
        'partner_id': sale.partner_id.id,
        'sale_id': sale.id,
        'amount': amount,
        'currency_id': sale.currency_id.id,
        'payment_date': datetime.date.today(),
        'payment_method': 'bank',
        'exchange_rate': 1.0
    })
    payment.action_post()

# Currency
try:
    usd = env.ref('base.USD')
    tryr = env.ref('base.TRY', raise_if_not_found=False)
    if not tryr:
         tryr = env['res.currency'].search([('name', '=', 'TRY')], limit=1)
except:
    usd = env['res.currency'].search([('name', '=', 'USD')], limit=1)
    tryr = env['res.currency'].search([('name', '=', 'TRY')], limit=1)

# Create Project: Skyline Towers
project_skyline = Project.create({
    'name': 'Skyline Towers',
    'city': 'Istanbul',
    'type_id': type_resi.id,
    'stage_id': stage_const.id,
    'gdv': 75000000.0,
    'currency_id': usd.id,
})
print(f"Created Project: {project_skyline.name}")

# Create Blocks
block_a = Block.create({'name': 'Tower A', 'project_id': project_skyline.id})
block_b = Block.create({'name': 'Tower B', 'project_id': project_skyline.id})

# Create Units (20 units)
units = []
floors = range(1, 11)
for i in floors:
    # Block A
    u_a = Unit.create({
        'project_id': project_skyline.id,
        'block_id': block_a.id,
        'name': f'A-{i}01',
        'floor': str(i),
        'gross_m2': 120,
        'net_m2': 100,
        'list_price': 250000 + (i * 2000),
        'state': 'available',
        'status_id': status_avail.id,
        'category_id': cat_2.id if i % 2 == 0 else cat_1.id
    })
    units.append(u_a)
    
    # Block B
    u_b = Unit.create({
        'project_id': project_skyline.id,
        'block_id': block_b.id,
        'name': f'B-{i}01',
        'floor': str(i),
        'gross_m2': 150,
        'net_m2': 130,
        'list_price': 350000 + (i * 3000),
        'state': 'available',
        'status_id': status_avail.id,
        'category_id': cat_duplex.id if i > 8 else cat_2.id
    })
    units.append(u_b)

print(f"Created {len(units)} units")

# Create Partners
buyer_names = ['John Doe', 'Alice Smith', 'Bob Jones', 'Emma Wilson', 'Michael Brown']
buyers = []
for name in buyer_names:
    existing = Partner.search([('name', '=', name)], limit=1)
    if existing:
        buyers.append(existing)
    else:
        buyers.append(Partner.create({'name': name, 'email': f'{name.lower().replace(" ", "")}@example.com', 'is_company': False}))

# Scenarios
# 1. Fully Paid
sale1 = create_sale_logic(env, units[0], buyers[0], 250000, 12, '2025-01-01', usd, sale_stage_signed)
pay_sale_logic(env, sale1, 250000)
print("Created fully paid sale")

# 2. Overdue
sale2 = create_sale_logic(env, units[1], buyers[1], 255000, 12, '2025-06-01', usd, sale_stage_legal)
pay_sale_logic(env, sale2, 255000 * (2/12)) # Only 2 months paid
print("Created overdue sale")

# 3. Upcoming
sale3 = create_sale_logic(env, units[2], buyers[2], 350000, 24, '2025-12-01', usd, sale_stage_signed)
pay_sale_logic(env, sale3, 350000 * (1/24))
print("Created upcoming sale")

# 4. Partial
sale4 = create_sale_logic(env, units[3], buyers[3], 360000, 12, '2025-08-01', usd, sale_stage_draft)
pay_sale_logic(env, sale4, 360000 * 0.4)

# 5. Recent Sale
units[4].state = 'option'
units[4].status_id = status_res.id
sale5 = create_sale_logic(env, units[5], buyers[4], 280000, 36, '2026-01-01', usd, sale_stage_signed)

env.cr.commit()
print("Data Generation Complete!")
