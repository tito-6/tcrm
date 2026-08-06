#!/usr/bin/env python3
"""Clear ORM/QWeb caches and compiled web asset attachments for one DB."""
import argparse
import sys

sys.path.insert(0, "/opt/tcrm/tcrm-src")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", required=True)
    parser.add_argument("-d", "--database", required=True)
    args = parser.parse_args()

    from tcrm.tools import config
    from tcrm.modules.registry import Registry
    from tcrm import api, SUPERUSER_ID

    config.parse_config(["-c", args.config, "-d", args.database])
    reg = Registry(args.database)
    with reg.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        env.registry.clear_cache()
        try:
            env["ir.qweb"].clear_caches()
        except Exception as exc:  # noqa: BLE001
            print("qweb_warn", exc)
        cr.execute(
            """
            DELETE FROM ir_attachment
            WHERE url LIKE '/web/assets/%' OR name LIKE 'web.assets_%'
            """
        )
        n = cr.rowcount
        cr.commit()
        print("cache_ok", args.database, "assets_deleted", n)


if __name__ == "__main__":
    main()
