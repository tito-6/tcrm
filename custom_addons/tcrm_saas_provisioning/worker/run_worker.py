#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TCRM privileged tenant-provisioning worker.

Runs OUTSIDE the web request path (systemd timer / manual / cron). It claims
signed provisioning jobs from the control database and provisions a dedicated,
isolated tenant database.

Security properties:
  * Never takes a database name, module list, shell command or admin password
    from browser input — everything is read from the (already validated) job row
    and from server-side config.
  * Uses Odoo's own service function to create the empty database and a fixed
    ``argv`` subprocess (``shell=False``) to initialise + install the version-
    locked module set — no shell interpolation.
  * Never copies software-owner Twilio / Meta / AI credentials into a tenant;
    it asserts tenant integration settings are empty.
  * Activates the tenant only after DB, module and isolation checks pass.
  * Idempotent: a failed job can be retried; a leftover half-built DB is dropped
    and rebuilt. A partially provisioned tenant is never activated.
  * Concurrency-safe: jobs are claimed with ``FOR UPDATE SKIP LOCKED`` and each
    tenant is guarded by a PostgreSQL advisory lock.

Usage:
    python run_worker.py -c /opt/tcrm/tcrm.prod.conf --control-db tcrm_master --once
    python run_worker.py -c /opt/tcrm/tcrm.prod.conf --loop --interval 30
"""
import argparse
import logging
import os
import secrets
import socket
import string
import subprocess
import sys
import time

_logger = logging.getLogger('tcrm.provisioning.worker')


# --------------------------------------------------------------------------- #
# Odoo bootstrap
# --------------------------------------------------------------------------- #
def _bootstrap_odoo(conf_path):
    import tcrm  # noqa: F401  (the platform package)
    from tcrm.tools import config as odoo_config
    argv = []
    if conf_path:
        argv += ['-c', conf_path]
    odoo_config.parse_config(argv)
    # Ensure the addons paths are on the import path so
    # ``tcrm.addons.tcrm_saas_provisioning`` is importable in this process.
    try:
        from tcrm.modules.module import initialize_sys_path
        initialize_sys_path()
    except Exception:
        _logger.exception('initialize_sys_path failed (continuing)')
    return odoo_config


def _gen_password(n=18):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(n))


def _advisory_key(tenant_id):
    # Stable 63-bit key space; namespaced away from 0.
    return 0x54435250_00000000 | (int(tenant_id) & 0xFFFFFFFF)


def _queue_ssl_for_domain(domain):
    """Ask the root SSL expander to cover this hostname (or the platform wildcard).

    The worker runs as ``tcrm`` with NoNewPrivileges, so it cannot run certbot.
    It drops a spool file consumed by ``ensure_tenant_ssl.sh --from-spool`` and
    best-effort kicks ``tcrm-ssl.service`` via sudoers (immediate, not timer-only).
    """
    d = (domain or '').strip().lower().rstrip('.')
    if not d or ('/' in d) or ('..' in d) or (' ' in d):
        return False
    if not (d.endswith('.tcrm.online') or d in ('tcrm.online', 'www.tcrm.online')):
        return False
    spool_dir = os.environ.get('TCRM_SSL_SPOOL_DIR', '/var/lib/tcrm/ssl-pending')
    try:
        os.makedirs(spool_dir, mode=0o755, exist_ok=True)
        safe = d.replace('/', '_').replace('\\', '_')
        path = os.path.join(spool_dir, '%s.domain' % safe)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(d + '\n')
        _logger.info('Queued SSL expand for %s (%s)', d, path)
        # Kick the oneshot service immediately when sudoers allows it.
        try:
            subprocess.run(
                ['sudo', '-n', 'systemctl', 'start', 'tcrm-ssl.service'],
                check=False, capture_output=True, text=True, timeout=30,
            )
        except Exception:
            _logger.debug('Could not kick tcrm-ssl.service; timer will pick it up',
                          exc_info=True)
        return True
    except Exception:
        _logger.exception('Failed to queue SSL expand for %s', d)
        return False


# --------------------------------------------------------------------------- #
# Provisioning steps
# --------------------------------------------------------------------------- #
def _pg_db_exists(db_name):
    """True if a PostgreSQL database exists (does not rely on list_db)."""
    import psycopg2
    from tcrm.tools import config as odoo_config
    conn = psycopg2.connect(
        dbname='postgres',
        user=odoo_config['db_user'],
        password=odoo_config['db_password'] or None,
        host=odoo_config['db_host'] or None,
        port=odoo_config['db_port'] or None,
    )
    try:
        conn.set_session(autocommit=True)
        with conn.cursor() as cr:
            cr.execute('SELECT 1 FROM pg_database WHERE datname = %s', (db_name,))
            return bool(cr.fetchone())
    finally:
        conn.close()


def _drop_database_if_exists(db_name):
    """Drop a leftover tenant DB for idempotent retry.

    Must NOT use ``exp_drop`` — with ``list_db=False`` Odoo raises AccessDenied
    even for the privileged worker. Use a direct Postgres DROP instead.
    """
    import psycopg2
    from tcrm.tools import config as odoo_config
    from tcrm.addons.tcrm_saas_provisioning.models import provisioning_common as pc

    pc.validate_db_name(db_name)
    if not _pg_db_exists(db_name):
        return
    _logger.warning('Dropping leftover database %s for idempotent retry', db_name)
    conn = psycopg2.connect(
        dbname='postgres',
        user=odoo_config['db_user'],
        password=odoo_config['db_password'] or None,
        host=odoo_config['db_host'] or None,
        port=odoo_config['db_port'] or None,
    )
    try:
        conn.set_session(autocommit=True)
        with conn.cursor() as cr:
            # Terminate sessions holding the DB open.
            cr.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (db_name,),
            )
            cr.execute('DROP DATABASE IF EXISTS "%s"' % db_name)
    finally:
        conn.close()


def _create_empty_db(db_name):
    from tcrm.service import db as service_db
    # Canonical, list_db-independent creation (correct encoding/collation/template).
    service_db._create_empty_database(db_name)


def _init_modules_subprocess(conf_path, db_name, module_csv, odoo_bin, http_port):
    """Initialise the tenant DB and install the module set via a fixed argv
    subprocess. No shell, no interpolation — db_name/module_csv are already
    validated to a strict charset upstream."""
    python = sys.executable
    argv = [
        python, odoo_bin,
        '-c', conf_path,
        '-d', db_name,
        '-i', module_csv,
        '--stop-after-init',
        '--no-http',
        '--http-port', str(http_port),
        '--without-demo=all',
        '--load-language=tr_TR',
        '--log-level=warn',
    ]
    _logger.info('Init subprocess: %s', ' '.join(argv))
    proc = subprocess.run(
        argv, shell=False, capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(odoo_bin)) or None, timeout=3600)
    tail = (proc.stdout or '')[-2000:] + '\n' + (proc.stderr or '')[-4000:]
    if proc.returncode != 0:
        raise RuntimeError('Odoo init failed (rc=%s):\n%s' % (proc.returncode, tail))
    return tail


def _configure_and_check_tenant(db_name, tenant_name, module_list,
                                 admin_login=None, admin_password=None):
    """Open the freshly initialised tenant DB, create company + initial admin,
    ensure integration settings are EMPTY, then run isolation/module checks.

    If admin_login/admin_password were set on the signed job by the control
    plane, use those; otherwise generate a one-time password and keep login
    ``admin``.

    Returns (admin_login, admin_password)."""
    from tcrm.modules.registry import Registry
    from tcrm import api, SUPERUSER_ID
    from tcrm.addons.tcrm_saas_provisioning.models import provisioning_common as pc

    registry = Registry(db_name)
    wanted_login = (admin_login or 'admin').strip() or 'admin'
    wanted_password = admin_password or _gen_password()

    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        # 1) Company: rename the default company to the tenant brand.
        company = env['res.company'].search([], order='id asc', limit=1)
        if not company:
            raise RuntimeError('No company in tenant DB after init.')
        company.write({'name': tenant_name})
        # Default CRM / accounting currency: Turkish Lira (TRY)
        try_cur = env['res.currency'].with_context(active_test=False).search(
            [('name', '=', 'TRY')], limit=1
        )
        country_tr = env.ref('base.tr', raise_if_not_found=False)
        currency_vals = {}
        if try_cur:
            if not try_cur.active:
                try_cur.active = True
            currency_vals['currency_id'] = try_cur.id
        if country_tr:
            currency_vals['country_id'] = country_tr.id
        if currency_vals:
            try:
                company.write(currency_vals)
            except Exception as exc:  # noqa: BLE001
                _logger.warning(
                    'Could not set TRY currency on tenant company: %s', exc
                )

        # 2) Initial administrator (control-plane credentials or generated).
        admin = env.ref('base.user_admin', raise_if_not_found=False)
        if not admin:
            admin = env['res.users'].search([('login', '=', 'admin')], limit=1)
        if not admin:
            raise RuntimeError('No administrator user in tenant DB after init.')
        admin.write({
            'name': '%s Administrator' % tenant_name,
            'login': wanted_login,
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
            'password': wanted_password,
        })
        admin_login = admin.login
        admin_password = wanted_password

        # 3) Empty tenant integration settings — never copy owner credentials.
        if 'tcrm.call.provider.config' in env:
            cfg = env['tcrm.call.provider.config'].search([], limit=1)
            if not cfg:
                cfg = env['tcrm.call.provider.config'].create({'enabled': False})
            else:
                cfg.write({'enabled': False})

        # 4) Assert NO sensitive credentials leaked into the tenant.
        for model_name, cred_fields in pc.SENSITIVE_CREDENTIAL_CHECKS:
            if model_name not in env:
                continue
            for rec in env[model_name].search([]):
                for f in cred_fields:
                    if f in rec._fields and rec[f]:
                        raise RuntimeError(
                            'Isolation violation: %s.%s is populated in a new tenant.'
                            % (model_name, f))

        # 5) Module check — every requested module must be installed.
        wanted = set(module_list)
        installed = set(env['ir.module.module'].search([
            ('name', 'in', list(wanted)), ('state', '=', 'installed')]).mapped('name'))
        missing = wanted - installed
        if missing:
            raise RuntimeError('Modules not installed: %s' % ', '.join(sorted(missing)))

        cr.commit()

    return admin_login, admin_password


# --------------------------------------------------------------------------- #
# Job processing
# --------------------------------------------------------------------------- #
def _process_one(conf_path, control_db, odoo_bin, http_port):
    """Claim and process a single job. Returns True if a job was handled."""
    from tcrm.modules.registry import Registry
    from tcrm import api, SUPERUSER_ID
    from tcrm.addons.tcrm_saas_provisioning.models import provisioning_common as pc

    worker_host = socket.gethostname()
    registry = Registry(control_db)

    # --- Phase 1: claim a job (own short transaction) ---
    job_id = tenant_id = None
    db_name = tenant_name = module_csv = None
    requested_login = requested_password = None
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        job = env['tcrm.provisioning.job'].claim_next(worker_host=worker_host)
        if not job:
            return False
        job_id = job.id
        tenant = job.tenant_id
        tenant_id = tenant.id
        db_name = job.db_name
        tenant_name = tenant.name
        module_csv = job.module_set or ''
        requested_login = job.admin_login or None
        requested_password = job.admin_password or None
        tenant.write({'provision_state': 'provisioning'})
        cr.commit()

    _logger.info('Claimed job %s: tenant=%s db=%s', job_id, tenant_id, db_name)

    # Validate inputs again (defense in depth) before doing anything destructive.
    try:
        pc.validate_db_name(db_name)
        module_list = pc.parse_module_set(module_csv)
        module_csv = ','.join(module_list)
    except ValueError as exc:
        _finalize(registry, job_id, tenant_id, ok=False, error='Validation: %s' % exc)
        return True

    # --- Phase 2: provision under a per-tenant advisory lock ---
    lock_conn = None
    try:
        from tcrm.sql_db import db_connect
        lock_conn = db_connect(control_db).cursor()
        lock_conn.execute('SELECT pg_try_advisory_lock(%s)', (_advisory_key(tenant_id),))
        got = lock_conn.fetchone()[0]
        if not got:
            _logger.warning('Tenant %s already locked by another worker; skipping', tenant_id)
            _finalize(registry, job_id, tenant_id, ok=False,
                      error='Tenant locked by another provisioning worker.', requeue=True)
            return True

        _drop_database_if_exists(db_name)          # idempotent retry cleanup
        _create_empty_db(db_name)                  # step: create PG database
        init_log = _init_modules_subprocess(       # step: init + install modules
            conf_path, db_name, module_csv, odoo_bin, http_port)
        admin_login, admin_pw = _configure_and_check_tenant(  # company + admin + checks
            db_name, tenant_name, module_list,
            admin_login=requested_login,
            admin_password=requested_password,
        )

        _finalize(registry, job_id, tenant_id, ok=True,
                  db_name=db_name, admin_login=admin_login, admin_password=admin_pw,
                  log=init_log[-1500:])
        _logger.info('Provisioning SUCCEEDED for tenant %s (db=%s)', tenant_id, db_name)
    except Exception as exc:  # noqa: BLE001 — worker must never crash the loop
        _logger.exception('Provisioning FAILED for tenant %s', tenant_id)
        _finalize(registry, job_id, tenant_id, ok=False, error=str(exc))
    finally:
        if lock_conn is not None:
            try:
                lock_conn.execute('SELECT pg_advisory_unlock(%s)', (_advisory_key(tenant_id),))
                lock_conn.commit()
            except Exception:
                pass
            try:
                lock_conn.close()
            except Exception:
                pass
    return True


def _finalize(registry, job_id, tenant_id, ok, db_name=None, admin_login=None,
              admin_password=None, log=None, error=None, requeue=False):
    from tcrm import api, SUPERUSER_ID
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        job = env['tcrm.provisioning.job'].browse(job_id)
        tenant = env['tcrm.tenant'].browse(tenant_id)
        if ok:
            job.mark_succeeded(log=log, admin_login=admin_login, admin_password=admin_password)
            tenant.write({
                'provision_state': 'provisioned',
                'state': 'active',
                'active': True,
                'db_name': db_name or tenant.db_name,
            })
            # Activate primary domain so routing resolves the tenant.
            # SSL is NOT assumed active — queue a cert expand for platform hosts.
            primary = tenant.domain_ids.filtered(lambda d: d.is_primary) or tenant.domain_ids
            if primary:
                dom = primary[:1]
                domain_name = (dom.domain or '').strip().lower()
                is_platform = (
                    domain_name.endswith('.tcrm.online')
                    or domain_name in ('tcrm.online', 'www.tcrm.online')
                )
                ssl = 'pending' if is_platform else (dom.ssl_status or 'pending')
                if is_platform and _queue_ssl_for_domain(domain_name):
                    ssl = 'pending'
                dom.write({'active': True, 'verified': True, 'ssl_status': ssl})
        else:
            if requeue:
                job.write({'state': 'queued'})
                tenant.write({'provision_state': 'queued'})
            else:
                job.mark_failed(error=error, log=log)
                tenant.write({'provision_state': 'failed'})
        cr.commit()


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main(argv=None):
    parser = argparse.ArgumentParser(description='TCRM tenant provisioning worker')
    parser.add_argument('-c', '--config', required=True, help='Path to tcrm.conf')
    parser.add_argument('--control-db', default='tcrm_master', help='Control-plane database')
    parser.add_argument('--odoo-bin', default=None, help='Path to tcrm-bin (default: guess)')
    parser.add_argument('--http-port', type=int, default=8899,
                        help='Spare HTTP port for the init subprocess')
    parser.add_argument('--once', action='store_true', help='Process one job then exit')
    parser.add_argument('--loop', action='store_true', help='Poll continuously')
    parser.add_argument('--interval', type=int, default=30, help='Loop poll seconds')
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')

    odoo_bin = args.odoo_bin
    if not odoo_bin:
        # Guess: <src>/tcrm-bin next to the addons.
        guess = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'tcrm-src', 'tcrm-bin')
        odoo_bin = guess
    if not os.path.exists(odoo_bin):
        _logger.error('tcrm-bin not found at %s; pass --odoo-bin', odoo_bin)
        return 2

    # Make the platform package importable: Python puts THIS script's directory on
    # sys.path (not the cwd), so add the source root (dir containing tcrm-bin).
    src_root = os.path.dirname(os.path.abspath(odoo_bin))
    if src_root not in sys.path:
        sys.path.insert(0, src_root)

    _bootstrap_odoo(args.config)

    if args.loop:
        _logger.info('Provisioning worker loop started (interval=%ss)', args.interval)
        while True:
            try:
                handled = _process_one(args.config, args.control_db, odoo_bin, args.http_port)
            except Exception:
                _logger.exception('Worker iteration error')
                handled = False
            if not handled:
                time.sleep(args.interval)
    else:
        handled = _process_one(args.config, args.control_db, odoo_bin, args.http_port)
        _logger.info('Processed a job.' if handled else 'No queued jobs.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
