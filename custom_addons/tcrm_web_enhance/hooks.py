# -*- coding: utf-8 -*-
"""Platform hooks for TCRM Web Enhance."""

import logging
import re

_logger = logging.getLogger(__name__)

# Public nav items to hide (Shop / Events / Forum / Blog / Courses)
_HIDDEN_MENU_URLS = (
    '/shop',
    '/event',
    '/forum',
    '/blog',
    '/slides',
)

_HIDDEN_MENU_NAMES = (
    'Shop', 'Mağaza',
    'Events', 'Etkinlikler',
    'Forum',
    'Blog',
    'Courses', 'Kurslar',
)


def _hide_public_website_menus(env):
    """Hide ecommerce/community menus from anonymous visitors."""
    Menu = env['website.menu'].sudo()
    internal = env.ref('base.group_user', raise_if_not_found=False)
    if not internal:
        return

    menus = Menu.search([
        '|',
        ('url', 'in', list(_HIDDEN_MENU_URLS)),
        ('name', 'in', list(_HIDDEN_MENU_NAMES)),
    ])
    # Also match localized URL prefixes like /tr/shop
    extra = Menu.search([
        '|', '|', '|', '|',
        ('url', '=like', '%/shop'),
        ('url', '=like', '%/event'),
        ('url', '=like', '%/forum'),
        ('url', '=like', '%/blog'),
        ('url', '=like', '%/slides'),
    ])
    menus |= extra
    if menus:
        menus.write({'group_ids': [(6, 0, [internal.id])]})
        _logger.info('Restricted %s public website menus to internal users', len(menus))


def _force_contactus_crm_lead(env):
    """Ensure contactus website forms create crm.lead, not mail.mail."""
    View = env['ir.ui.view'].sudo()
    views = View.search([
        '|',
        ('key', 'ilike', 'contactus'),
        ('name', 'ilike', 'contact'),
        ('type', '=', 'qweb'),
    ])
    updated = 0
    for view in views:
        arch = view.arch_db or ''
        if 'data-model_name="mail.mail"' in arch and (
            'contactus_form' in arch or 's_website_form' in arch
        ):
            view.write({
                'arch_db': arch.replace(
                    'data-model_name="mail.mail"',
                    'data-model_name="crm.lead"',
                ),
            })
            updated += 1
    if updated:
        _logger.info('Rewrote %s contact form view(s) to use crm.lead', updated)


def _rename_company_to_akod(env):
    """Rename public company / website branding AK KOD → AKOD."""
    Company = env['res.company'].sudo()
    for company in Company.search([]):
        name = company.name or ''
        if 'AK KOD' in name or name.strip() == 'AK KOD':
            company.write({'name': name.replace('AK KOD', 'AKOD')})
    Website = env['website'].sudo()
    for website in Website.search([]):
        vals = {}
        if website.name and 'AK KOD' in website.name:
            vals['name'] = website.name.replace('AK KOD', 'AKOD')
        # company_id name is enough for most brand surfaces
        if vals:
            website.write(vals)


def _reset_homepage_product_block(env):
    """
    Ensure the homepage inherit no longer carries the Product/Services/Careers
    block if a COW (website-editor) copy still has it.
    """
    View = env['ir.ui.view'].sudo()
    views = View.search([
        '|',
        ('key', '=', 'tcrm_web_enhance.tcrm_homepage'),
        ('name', 'ilike', 'TCRM Homepage'),
    ])
    pattern = re.compile(
        r'<section class="s_text_block pt64 pb64">\s*'
        r'<div class="container">\s*'
        r'<div class="row g-4">.*?</div>\s*'
        r'</div>\s*'
        r'</section>',
        re.DOTALL,
    )
    for view in views:
        arch = view.arch_db or ''
        if 'View products' in arch or 'Ürünleri görüntüle' in arch or 'Explore what TCRM' in arch:
            new_arch = pattern.sub('', arch)
            if new_arch != arch:
                view.write({'arch_db': new_arch})
                _logger.info('Removed Product/Services/Careers block from view %s', view.id)


def post_init_hook(env):
    env['ir.module.module']._tcrm_hide_apps_gallery_for_tenants()
    env['ir.ui.menu']._tcrm_fix_missing_web_icons()
    _hide_public_website_menus(env)
    _force_contactus_crm_lead(env)
    _rename_company_to_akod(env)
    _reset_homepage_product_block(env)
    env['ir.module.module']._tcrm_disable_tcrm_com_oauth_login()
    if hasattr(env['res.company'], '_tcrm_ensure_try_currency'):
        env['res.company']._tcrm_ensure_try_currency()
