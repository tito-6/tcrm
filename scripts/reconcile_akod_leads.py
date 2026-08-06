# -*- coding: utf-8 -*-
"""
Reconciliation script for akod.tech leads.

Migrates misrouted leads created in `tcrm_master` during the routing issue
to their target tenant database `akod_prod`.

Usage:
  # Dry-run (preview only):
  python scripts/reconcile_akod_leads.py

  # Apply migration:
  python scripts/reconcile_akod_leads.py --apply
"""
import sys
import os
import argparse
import json

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TCRM_SRC = r"d:\crm\tcrm-src"

sys.path.insert(0, TCRM_SRC)
sys.path.insert(0, PROJECT_ROOT)

import tcrm
from tcrm.tools import config
config.parse_config(['-c', os.path.join(PROJECT_ROOT, 'tcrm.conf')])

from tcrm.api import Environment
from tcrm.sql_db import db_connect


MASTER_DB = "tcrm_master"
TENANT_DB = "akod_prod"


def find_misrouted_leads():
    conn = db_connect(MASTER_DB)
    cr = conn.cursor()
    
    query = """
        SELECT id, name, contact_name, email_from, phone, partner_name, city, description, type,
               meta_source, meta_raw_payload, meta_leadgen_id, create_date
        FROM crm_lead
        WHERE meta_source = 'akod_website'
           OR email_from LIKE '%akod.tech%'
           OR name LIKE '%Iletisim Formu%'
        ORDER BY id ASC;
    """
    cr.execute(query)
    rows = cr.fetchall()
    
    records = []
    for r in rows:
        records.append({
            'id': r[0],
            'name': r[1],
            'contact_name': r[2],
            'email_from': r[3],
            'phone': r[4],
            'partner_name': r[5],
            'city': r[6],
            'description': r[7],
            'type': r[8],
            'meta_source': r[9],
            'meta_raw_payload': r[10],
            'meta_leadgen_id': r[11],
            'create_date': str(r[12]),
        })
    cr.close()
    return records



def reconcile_leads(apply_changes=False):
    print(f"=== AKOD.TECH LEAD RECONCILIATION ===")
    print(f"Source DB: {MASTER_DB}")
    print(f"Target DB: {TENANT_DB}")
    print(f"Mode: {'APPLY MIGRATION' if apply_changes else 'DRY RUN (PREVIEW)'}")
    print("=" * 40)
    
    misrouted = find_misrouted_leads()
    print(f"Found {len(misrouted)} misrouted lead(s) in {MASTER_DB}:\n")
    
    for idx, item in enumerate(misrouted, 1):
        print(f"[{idx}] ID: {item['id']} | Name: {item['name']} | Email: {item['email_from']} | Date: {item['create_date']}")
    
    if not misrouted:
        print("\nNo misrouted leads found to reconcile.")
        return
        
    if not apply_changes:
        print("\n[DRY RUN] Run with '--apply' flag to execute migration into akod_prod.")
        return
        
    print("\nStarting migration into akod_prod...")
    
    conn_t = db_connect(TENANT_DB)
    cr_t = conn_t.cursor()
    env_t = Environment(cr_t, 1, {})
    Lead_t = env_t['crm.lead'].sudo()
    
    # Get tenant defaults
    company = env_t['res.company'].sudo().search([], limit=1)
    company_id = company.id if company else False
    
    stages = env_t['crm.stage'].sudo().search([], order='sequence asc, id asc')
    stage_id = stages[0].id if stages else False
    
    teams = env_t['crm.team'].sudo().search([('active', '=', True)], limit=1)
    team_id = teams[0].id if teams else False
    
    migrated_count = 0
    skipped_count = 0
    
    for item in misrouted:
        # Check if already exists in target DB by email or meta_leadgen_id
        domain = []
        if item.get('meta_leadgen_id'):
            domain.append(('meta_leadgen_id', '=', item['meta_leadgen_id']))
        elif item.get('email_from'):
            domain.append(('email_from', '=', item['email_from']))
        else:
            domain.append(('name', '=', item['name']))
            
        existing = Lead_t.search(domain, limit=1)
        if existing:
            print(f"  - Skipping Lead '{item['name']}' (ID {item['id']}): already exists in {TENANT_DB} with ID {existing.id}")
            skipped_count += 1
            continue
            
        new_lead_data = {
            'name': item['name'],
            'contact_name': item['contact_name'],
            'email_from': item['email_from'],
            'phone': item['phone'],
            'partner_name': item['partner_name'],
            'city': item['city'],
            'description': (item['description'] or '') + f"\n\n[Reconciled from tcrm_master ID {item['id']}]",
            'type': 'lead',  # Convert to lead so it appears in Lead Havuzu
            'company_id': company_id,
            'stage_id': stage_id,
            'team_id': team_id,
            'meta_platform': 'website',
            'meta_source': 'akod_website',
            'meta_medium': 'organic',
        }
        if item.get('meta_leadgen_id'):
            new_lead_data['meta_leadgen_id'] = item['meta_leadgen_id']
        if item.get('meta_raw_payload'):
            new_lead_data['meta_raw_payload'] = item['meta_raw_payload']
            
        new_lead = Lead_t.create(new_lead_data)
        print(f"  + Migrated Lead '{item['name']}' (Old ID: {item['id']} -> New ID in {TENANT_DB}: {new_lead.id})")
        migrated_count += 1
        
    cr_t.commit()
    cr_t.close()
    
    print("\n" + "=" * 40)
    print(f"Reconciliation Complete. Migrated: {migrated_count}, Skipped: {skipped_count}.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Reconcile akod.tech leads")
    parser.add_argument('--apply', action='store_true', help="Execute migration changes")
    args = parser.parse_args()
    reconcile_leads(apply_changes=args.apply)
