# Apply AK KOD branding + refresh menu icons. Run via tcrm-bin shell.
import base64
from pathlib import Path

ROOT = Path(r"d:\tcrm")
LOGO_SVG = ROOT / "tcrm-src/addons/web/static/img/tcrm_logo.svg"
LOGO_PNG = ROOT / "tcrm-src/addons/web/static/img/tcrm_logo_tiny.png"

COMPANY_NAME = "AK KOD YAZILIM BİLİŞİM LTD. ŞTİ."
PHONE = "05525242866"
EMAIL = "info@akod.tech"
WEBSITE_URL = "https://akod.tech/"
STREET = "Karanfil Sokak No:13"
CITY = "Besiktas"
ZIP = "34330"
COUNTRY = env.ref("base.tr", raise_if_not_found=False)

company = env.company
vals = {
    "name": COMPANY_NAME,
    "phone": PHONE,
    "email": EMAIL,
    "website": WEBSITE_URL,
    "street": STREET,
    "city": CITY,
    "zip": ZIP,
    "social_facebook": "https://www.facebook.com/akkoddijital",
    "social_linkedin": "https://www.linkedin.com/company/ak-kod/",
    "social_instagram": "https://www.instagram.com/akkod_yazilim/",
    "social_twitter": False,
}
if COUNTRY:
    vals["country_id"] = COUNTRY.id
# Prefer a real raster logo. A mislabeled SVG (.png extension) breaks /web/image.
def _is_real_png(path: Path) -> bool:
    try:
        return path.exists() and path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    except OSError:
        return False

logo_png = ROOT / "tcrm-src/addons/web/static/img/logo.png"
if _is_real_png(logo_png):
    logo_path = logo_png
elif _is_real_png(LOGO_PNG):
    logo_path = LOGO_PNG
else:
    logo_path = LOGO_SVG
vals["logo"] = base64.b64encode(logo_path.read_bytes())
print("logo source:", logo_path)
company.sudo().write(vals)
print("company updated:", company.name, company.phone)

website = env["website"].search([], limit=1)
website.sudo().write({
    "name": "TCRM",
    "logo": vals["logo"],
    "social_facebook": "https://www.facebook.com/akkoddijital",
    "social_linkedin": "https://www.linkedin.com/company/ak-kod/",
    "social_instagram": "https://www.instagram.com/akkod_yazilim/",
    "social_twitter": False,
})
print("website updated:", website.name)

# Disable Odoo/Tcrm.com OAuth on login
oauth = env["auth.oauth.provider"].sudo().search([("name", "ilike", "Tcrm.com")])
oauth.write({"enabled": False})
print("disabled oauth:", oauth.mapped("name"))

# Refresh menu icons from regenerated FA PNGs
ICON_BY_XMLID = {
    "base.menu_administration": "base,static/description/settings.png",
    "base.menu_management": "base,static/description/modules.png",
    "tcrm_saas_core.menu_tcrm_root": "tcrm_saas_core,static/description/icon.png",
    "tcrm_ai.menu_tcrm_ai_root": "tcrm_ai,static/description/icon.png",
    "tcrm_ai_research.menu_tcrm_ai_research_root": "tcrm_ai_research,static/description/icon.png",
    "tcrm_research_hub.menu_research_hub_root": "tcrm_research_hub,static/description/icon.png",
    "tcrm_propertio.menu_propertio_root": "tcrm_propertio,static/description/icon.png",
}
for xmlid, web_icon in ICON_BY_XMLID.items():
    menu = env.ref(xmlid, raise_if_not_found=False)
    if menu:
        menu.sudo().write({"web_icon": web_icon})
        print("icon", xmlid)

# Update contactus page phone / company blurbs if present
Contact = env["website.page"].sudo().search([("url", "=", "/contactus")], limit=1)
if Contact and Contact.view_id:
    arch = Contact.view_id.arch_db or ""
    # light replace of common placeholders when still default
    replacements = {
        "+1 555-555-5555": "0552 524 28 66",
        "+1 555-555-5556": "0552 524 28 66",
        "info@yourcompany.example.com": EMAIL,
        "Your Company": COMPANY_NAME,
        "My Company": COMPANY_NAME,
    }
    new_arch = arch
    for a, b in replacements.items():
        new_arch = new_arch.replace(a, b)
    if new_arch != arch:
        Contact.view_id.sudo().write({"arch_db": new_arch})
        print("contactus placeholders updated")

# Header call-to-action / text elements often store phone in ir.ui.view arch
views = env["ir.ui.view"].sudo().search([
    ("type", "=", "qweb"),
    "|", "|",
    ("arch_db", "ilike", "555-555"),
    ("arch_db", "ilike", "yourcompany"),
    ("arch_db", "ilike", "Company name"),
])
print("views with placeholders:", len(views))
for v in views:
    arch = v.arch_db or ""
    new_arch = arch
    for a, b in {
        "+1 555-555-5555": "0552 524 28 66",
        "+1 555-555-5556": "0552 524 28 66",
        "info@yourcompany.example.com": EMAIL,
        "Copyright &amp;copy; Company name": f"Copyright &amp;copy; {COMPANY_NAME}",
        "Copyright © Company name": f"Copyright © {COMPANY_NAME}",
    }.items():
        new_arch = new_arch.replace(a, b)
    if new_arch != arch:
        try:
            v.write({"arch_db": new_arch})
            print("patched view", v.key or v.id)
        except Exception as e:
            print("skip view", v.id, e)

env.registry.clear_cache()
env.cr.commit()
print("DONE branding")
