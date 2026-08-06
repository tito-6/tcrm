import re

views = env['ir.ui.view'].search([('arch_db', 'ilike', 's_text_block')])
for view in views:
    if 'Product' in view.arch_db and 'Services' in view.arch_db and 'Careers' in view.arch_db:
        # We found a view with the duplicated footer block
        print(f"Modifying view {view.id} ({view.name})")
        # Regex to remove the section block
        new_arch = re.sub(r'<section class="s_text_block[^>]*>.*?Explore what TCRM includes.*?</section>', '', view.arch_db, flags=re.DOTALL)
        # Also try replacing the exact block if regex fails
        if new_arch == view.arch_db:
            new_arch = re.sub(r'<section[^>]*s_text_block[^>]*>.*?Product.*?Services.*?Careers.*?</section>', '', view.arch_db, flags=re.DOTALL)
            
        view.arch_db = new_arch

env.cr.commit()
env.registry.clear_cache()
print("Cleaned up COW views.")
