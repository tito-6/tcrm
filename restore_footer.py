view = env['ir.ui.view'].browse(5605)
print("View key:", view.key)
print("View name:", view.name)
if view.website_id:
    view.unlink()
    print("Deleted COW view, should fallback to base view.")
else:
    # If it's a base view, just update the module again
    if view.arch_fs:
        view.arch_db = view.arch_fs
        print("Reverted base view to arch_fs.")
    else:
        print("No arch_fs found to revert to!")

env.cr.commit()
env.registry.clear_cache()
