menu = env['website.menu'].search([('url', '=', '/jobs')], limit=1)
if menu:
    menu.name = 'Kariyer'
    env.cr.commit()
    print("Updated menu.")
else:
    print("Menu not found")
