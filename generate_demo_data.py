# from tcrm import api, SUPERUSER_ID
import random
from datetime import date, timedelta

def run(env):
    print(">>> STARTING EXPANDED DEMO DATA GENERATION...")
    
    # 1. CLEANUP
    print(">>> Cleaning old data...")
    try:
        sales = env['propertio.sale'].search([])
        if sales:
            payments = env['propertio.payment'].search([])
            if payments:
                payments.unlink()
            installments = env['propertio.installment'].search([])
            if installments:
                installments.unlink()
            sales.unlink()
            
        units = env['propertio.unit'].search([])
        if units:
            units.unlink()
            
        blocks = env['propertio.block'].search([])
        if blocks:
            blocks.unlink()
            
        projects = env['propertio.project'].search([])
        if projects:
            projects.unlink()
            
    except Exception as e:
        print(f">>> Warning during cleanup: {e}")

    # 2. CREATE PROJECTS
    print(">>> Creating Projects...")
    project_names = ['Sunrise Towers', 'Golden Valley', 'Blue Marines', 'Green Hills', 'Urban Loft']
    cities = ['Istanbul', 'Izmir', 'Bodrum', 'Bursa', 'Antalya']
    projects = []
    
    for i, name in enumerate(project_names):
        proj = env['propertio.project'].create({
            'name': name,
            'city': cities[i % len(cities)],
            'gdv': 10000000.0 * (i + 1),
            'unit_count': 0 # Will be calc automatically usually
        })
        projects.append(proj)
        
        # Create Blocks
        env['propertio.block'].create({'name': 'Block A', 'project_id': proj.id})
        env['propertio.block'].create({'name': 'Block B', 'project_id': proj.id})

    # 3. CREATE UNITS
    print(">>> Creating Units...")
    all_units = []
    for proj in projects:
        blocks = env['propertio.block'].search([('project_id', '=', proj.id)])
        for block in blocks:
            for i in range(1, 11): # 10 units per block
                floor = (i - 1) // 2 + 1
                u = env['propertio.unit'].create({
                    'name': f'{block.name.split()[-1]}-{i:02d}',
                    'project_id': proj.id,
                    'block_id': block.id,
                    'floor': str(floor),
                    'list_price': 200000 + (random.randint(1, 20) * 5000),
                    'gross_m2': 100 + random.randint(10, 50),
                    'net_m2': 80 + random.randint(10, 40),
                    'state': 'available'
                })
                all_units.append(u)

    # 4. CREATE CUSTOMERS
    print(">>> Creating Customers...")
    partners = []
    names = ['John Doe', 'Jane Smith', 'Michael Brown', 'Emily Davis', 'Chris Wilson']
    for n in names:
        p = env['res.partner'].create({'name': n, 'email': f"{n.replace(' ', '.').lower()}@example.com"})
        partners.append(p)
        
    agency = env['res.partner'].create({'name': 'Top Real Estate Agency', 'is_company': True})

    # 5. CREATE SALES & VARIED STATUSES
    print(">>> Creating Sales with Varied Statuses...")
    
    # Helper to create installments and payments
    def create_installments(sale, status_type):
        total = sale.sale_price
        
        # 1. Down Payment (Paid)
        dp = total * 0.20
        dp_due = date.today() - timedelta(days=60) # Past
        
        # Create Installment
        dp_inst = env['propertio.installment'].create({
            'sale_id': sale.id, 'name': 'Down Payment', 'amount': dp, 'amount_paid': 0.0, 
            'date_due': dp_due, 'type': 'down_payment', 'payment_status': 'overdue' # temporarily
        })

        # Create Payment to cover DP
        pay_dp = env['propertio.payment'].create({
            'name': 'PAY-DP-' + sale.name,
            'partner_id': sale.partner_id.id,
            'sale_id': sale.id,
            'amount': dp,
            'currency_id': sale.currency_id.id,
            'payment_date': dp_due,
            'payment_method': 'bank',
            'state': 'draft'
        })
        # Post payment (allocates to DP installment)
        pay_dp.action_post()
        
        rem_amount = (total - dp) / 10 # 10 installments
        
        for k in range(1, 11):
            if status_type == 'overdue_heavy':
                due_date = date.today() - timedelta(days=30 * (5 - k)) 
            elif status_type == 'upcoming_focused':
                due_date = date.today() + timedelta(days=30 * (k - 1))
            elif status_type == 'paid_full':
                due_date = date.today() - timedelta(days=30 * k)
            else: 
                due_date = date.today() + timedelta(days=30 * (k - 2)) 

            # Create Installment
            inst = env['propertio.installment'].create({
                'sale_id': sale.id, 'name': f'Inst {k}/10', 'amount': rem_amount, 'amount_paid': 0.0,
                'date_due': due_date, 'type': 'installment'
            })
            
            # Create Payment if needed
            if status_type == 'paid_full':
                pay = env['propertio.payment'].create({
                    'name': f'PAY-{k}-{sale.name}',
                    'partner_id': sale.partner_id.id,
                    'sale_id': sale.id,
                    'amount': rem_amount,
                    'currency_id': sale.currency_id.id,
                    'payment_date': due_date, # Paid on due date
                    'payment_method': 'bank',
                    'state': 'draft'
                })
                pay.action_post()
                
            elif status_type == 'overdue_heavy' and k < 3:
                 # partially paid maybe? No, let's leave overdue heavy unpaid for impact.
                 pass


    # Scenario 1: Overdue Customer
    u = all_units[0]
    s1 = env['propertio.sale'].create({
        'partner_id': partners[0].id, 'unit_id': u.id, 'sale_price': u.list_price, 
        'date_sale': date.today() - timedelta(days=60), 'state': 'confirmed', 'contract_no': 'OVER-001'
    })
    u.state = 'sold'
    create_installments(s1, 'overdue_heavy')
    s1._compute_totals()

    # Scenario 2: Paid Customer
    u = all_units[1]
    s2 = env['propertio.sale'].create({
        'partner_id': partners[1].id, 'unit_id': u.id, 'sale_price': u.list_price, 
        'date_sale': date.today() - timedelta(days=120), 'state': 'confirmed', 'contract_no': 'PAID-001'
    })
    u.state = 'sold'
    create_installments(s2, 'paid_full')
    s2._compute_totals()
    
    # Scenario 3: Upcoming / Normal
    u = all_units[2]
    s3 = env['propertio.sale'].create({
        'partner_id': partners[2].id, 'unit_id': u.id, 'sale_price': u.list_price, 
        'date_sale': date.today(), 'state': 'confirmed', 'contract_no': 'NORM-001'
    })
    u.state = 'sold'
    create_installments(s3, 'upcoming_focused')
    s3._compute_totals()
    
     # Scenario 4: Draft
    u = all_units[3]
    s4 = env['propertio.sale'].create({
        'partner_id': partners[3].id, 'unit_id': u.id, 'sale_price': u.list_price, 
        'date_sale': date.today(), 'state': 'draft', 'contract_no': 'DRAFT-001'
    })
    u.state = 'option'

    print(">>> EXPANDED DEMO DATA CREATED!")
    env.cr.commit()

if 'env' in locals():
    run(env)
