def check(env):
    mod = env['ir.module.module'].search([('name', '=', 'tcrm_propertio')])
    print(f">>> Module 'tcrm_propertio' State: '{mod.state}'")
    if mod.state != 'installed':
        print(">>> Attempting to install...")
        try:
             # Just set state to to install, easier for command line update to pick up, 
             # but button_immediate_install does it one go.
            mod.button_immediate_install()
            print(">>> Install triggered.")
        except Exception as e:
            print(f">>> Install failed: {e}")

if 'env' in locals():
    check(env)
