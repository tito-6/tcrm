env.cr.execute("SELECT conname FROM pg_constraint WHERE conname LIKE %s", ('%platform_ad%',))
print('db', env.cr.fetchall())
print('model', env['tcrm.marketing.meta.ad']._sql_constraints)
print('constraints attr', getattr(env['tcrm.marketing.meta.ad'], '_constraints', None))
