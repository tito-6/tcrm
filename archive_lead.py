env['crm.lead'].browse(625).write({'active': False})
env.cr.commit()
