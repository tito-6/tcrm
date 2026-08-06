
print("Starting Payment Status Recompute...")
installments = env['propertio.installment'].search([])
print(f"Found {len(installments)} installments.")
for inst in installments:
    inst._compute_payment_status()
    # Force write to ensure DB update
    # We write what was computed
    # Triggering write might be needed if Odoo doesn't detect change on computed field immediately in shell
    pass 

env.cr.commit()
print("Payment Status Recomputed and Committed.")
