import sys
import os
import random
import datetime
from dateutil.relativedelta import relativedelta

# Setup path to find tcrm package
sys.path.append(os.path.abspath("d:\\crm\\tcrm-src"))

import tcrm
from tcrm.tools import config

def generate_data():
    print("Initializing Odoo Environment...")
    config.parse_config(['generate_demo.py', '-c', 'tcrm.conf', '-d', 'tcrm_master'])
    
    # Initialize registry
    import tcrm.modules.registry
    registry = tcrm.modules.registry.Registry.new(config['db_name'])
    
    with registry.cursor() as cr:
        env = tcrm.api.Environment(cr, tcrm.SUPERUSER_ID, {})
        print("Connected to database. Starting data generation...")

        # 1. Create Projects
        Project = env['propertio.project']
        Block = env['propertio.block']
        Unit = env['propertio.unit']
        Partner = env['res.partner']
        Sale = env['propertio.sale']
        Installment = env['propertio.installment']
        Payment = env['propertio.payment']

        # Currency
        try:
            usd = env.ref('base.USD')
            try:
                tryr = env.ref('base.TRY')
            except:
                tryr = env['res.currency'].search([('name', '=', 'TRY')], limit=1)
        except ValueError:
            usd = env['res.currency'].search([('name', '=', 'USD')], limit=1)
            tryr = env['res.currency'].search([('name', '=', 'TRY')], limit=1)

        # Create Project: Skyline Towers
        project_skyline = Project.create({
            'name': 'Skyline Towers',
            'city': 'Istanbul',
            'project_type': 'mixed',
            'gdv': 50000000.0,
            'currency_id': usd.id,
        })
        print(f"Created Project: {project_skyline.name}")

        # Create Blocks
        block_a = Block.create({'name': 'Block A', 'project_id': project_skyline.id})
        block_b = Block.create({'name': 'Block B', 'project_id': project_skyline.id})
        
        # Create Units (20 units)
        units = []
        floors = range(1, 11)
        for i in floors:
            # Block A units
            u_a = Unit.create({
                'project_id': project_skyline.id,
                'block_id': block_a.id,
                'name': f'A-{i}01',
                'floor': str(i),
                'gross_m2': 120,
                'net_m2': 100,
                'list_price': 250000 + (i * 2000),
                'state': 'available'
            })
            units.append(u_a)
            
            # Block B units
            u_b = Unit.create({
                'project_id': project_skyline.id,
                'block_id': block_b.id,
                'name': f'B-{i}01',
                'floor': str(i),
                'gross_m2': 150,
                'net_m2': 130,
                'list_price': 350000 + (i * 3000),
                'state': 'available'
            })
            units.append(u_b)

        print(f"Created {len(units)} units")

        # Create Partners (Buyers)
        buyer_names = ['John Doe', 'Alice Smith', 'Bob Jones', 'Emma Wilson', 'Michael Brown']
        buyers = []
        for name in buyer_names:
            buyers.append(Partner.create({'name': name, 'email': f'{name.lower().replace(" ", "")}@example.com'}))

        # Create Sales (Sell 10 units)
        # Scenario 1: Fully Paid (Good Customer)
        sale1 = create_sale(env, units[0], buyers[0], 250000, 12, '2025-01-01', usd)
        pay_sale(env, sale1, 250000) # Pay all
        print("Created fully paid sale")

        # Scenario 2: Overdue (Bad Customer)
        sale2 = create_sale(env, units[1], buyers[1], 255000, 12, '2025-06-01', usd)
        # Pay only first 2 months. Now it's Jan 2026, so many are overdue.
        pay_sale(env, sale2, 255000 * (2/12)) 
        print("Created overdue sale")

        # Scenario 3: Upcoming (New Customer)
        sale3 = create_sale(env, units[2], buyers[2], 350000, 24, '2025-12-01', usd)
        pay_sale(env, sale3, 350000 * (1/24)) # Pay down payment
        print("Created new sale with upcoming installments")
        
        # Scenario 4: Partial Arrears
        sale4 = create_sale(env, units[3], buyers[3], 360000, 12, '2025-08-01', usd)
        pay_sale(env, sale4, 360000 * 0.4) # 40% paid
        
        # Scenario 5: Recent Sale (Option -> Sold)
        units[4].state = 'option'
        sale5 = create_sale(env, units[5], buyers[4], 280000, 36, '2026-01-01', usd)
        # No payments yet
        
        env.cr.commit()
        print("Data Generation Complete!")

def create_sale(env, unit, partner, price, installments, start_date_str, currency):
    # Wizard logic implemented manually
    Sale = env['propertio.sale']
    Installment = env['propertio.installment']
    
    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
    
    sale = Sale.create({
        'partner_id': partner.id,
        'unit_id': unit.id,
        'date_sale': start_date,
        'sale_price': price,
        'currency_id': currency.id,
        'state': 'confirmed'
    })
    
    unit.state = 'sold'
    
    # Create installments
    amount_per_install = price / installments
    
    for i in range(installments):
        date_due = start_date + relativedelta(months=i)
        Installment.create({
            'sale_id': sale.id,
            'name': f'{i+1}/{installments}',
            'date_due': date_due,
            'amount': amount_per_install,
            'type': 'regular'
        })
    
    return sale

def pay_sale(env, sale, amount):
    Payment = env['propertio.payment']
    
    # Create payment
    payment = Payment.create({
        'partner_id': sale.partner_id.id,
        'sale_id': sale.id,
        'amount': amount,
        'currency_id': sale.currency_id.id,
        'payment_date': datetime.date.today(),
        'payment_method': 'bank',
        'exchange_rate': 1.0 # Assume same currency for simplicity
    })
    payment.action_post()


if __name__ == "__main__":
    generate_data()
