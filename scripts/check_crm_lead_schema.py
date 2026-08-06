#!/usr/bin/env python3
"""Report missing stored crm.lead columns vs model fields for one DB."""
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
        if "crm.lead" not in env:
            print("no_crm_lead")
            return
        Lead = env["crm.lead"]
        cr.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='crm_lead'"
        )
        db = {r[0] for r in cr.fetchall()}
        missing = [
            n
            for n, f in Lead._fields.items()
            if getattr(f, "store", False)
            and f.type not in ("one2many", "many2many")
            and getattr(f, "column_type", None)
            and n not in db
        ]
        print("still_missing", missing)


if __name__ == "__main__":
    main()
