# Run via tcrm-bin shell
env = env  # noqa: F821
env = env(context=dict(env.context, tcrm_market_allow_master_company_ops=True))
env["ir.config_parameter"].sudo().set_param("tcrm_market_analysis.allow_master_listings", "1")

from tcrm.addons.tcrm_market_analysis.services.demo_seed import seed_company_demo

companies = env["res.company"].search([], order="id", limit=3)
print("company_count", len(companies))
for i, company in enumerate(companies):
    scenario = "istanbul" if i == 0 else "ankara_izmir"
    src = seed_company_demo(env, company, scenario=scenario)
    Sah = env["tcrm.market.source"].sudo()
    existing = Sah.search([("company_id", "=", company.id), ("source_type", "=", "sahibinden")], limit=1)
    if not existing:
        Sah.create({
            "name": "Sahibinden Public",
            "source_type": "sahibinden",
            "company_id": company.id,
            "authorization_state": "authorized",
            "state": "enabled",
            "filter_transaction": "sale",
            "filter_category": "daire",
            "filter_province": "Istanbul" if i == 0 else "Ankara",
            "filter_district": "Kadikoy" if i == 0 else "Cankaya",
            "max_pages": 2,
            "max_records": 40,
            "error_log": (
                "Live scrape blocked by Cloudflare HTTP 403 Just a moment. "
                "Demo listings loaded so UI is not empty."
            ),
            "scrape_state": "blocked",
            "scrape_progress_message": "Cloudflare blocked live fetch from this server",
        })
    n = env["tcrm.market.listing"].sudo().search_count([("company_id", "=", company.id)])
    print("seeded", company.id, "listings", n, "demo_source", src.id)
print("DONE")
env.cr.commit()
