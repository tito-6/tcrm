# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""
TCRM Mock Data builder.

Creates one coherent, cross-linked "Nova Estates" business scenario shared by
every TCRM module (CRM, Sales, Properties/Propertio, Contacts, Brokers,
Payments, Dashboards ...).

Design goals
------------
* **Idempotent**: every seed record is registered under a deterministic
  ``ir.model.data`` external id in the ``tcrm_mock_data`` namespace. Re-running
  :meth:`build_all` returns the existing record instead of creating a new one,
  so it never produces duplicate records.
* **Relationally consistent**: opportunities reference the project/unit they are
  about; property sales reference their CRM opportunity and broker; sold units
  have a confirmed contract; reserved units have an offer; installment plans sum
  to the sale price; payments are posted through the real ORM workflow so paid
  amounts stay consistent.
* **ORM-first**: records go through the normal ORM (create/confirm/post) so
  computed fields, sequences and side effects behave exactly like production.

Cross-method state is threaded through a plain ``reg`` dict (records cannot be
reliably stashed as attributes on an Odoo recordset).
"""
import logging
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from tcrm import api, models

_logger = logging.getLogger(__name__)

MODULE = "tcrm_mock_data"


class TcrmMockBuilder(models.TransientModel):
    _name = "tcrm.mock.builder"
    _description = "TCRM Mock Data Builder"

    # ------------------------------------------------------------------ helpers
    def _seed(self, xmlid, model, vals):
        """Create-or-get a record with a deterministic external id.

        The external id is ``tcrm_mock_data.<xmlid>``. If it already exists the
        existing record is returned untouched (idempotency); otherwise the record
        is created and the external id registered.
        """
        env = self.env
        rec = env.ref("%s.%s" % (MODULE, xmlid), raise_if_not_found=False)
        if rec:
            return rec
        rec = env[model].sudo().create(vals)
        env["ir.model.data"].sudo().create({
            "name": xmlid,
            "module": MODULE,
            "model": model,
            "res_id": rec.id,
            "noupdate": True,
        })
        return rec

    def _exists(self, xmlid):
        return bool(self.env.ref("%s.%s" % (MODULE, xmlid), raise_if_not_found=False))

    def _get_or_create(self, model, domain, vals):
        """Search-or-create shared master data that may already exist (no xmlid)."""
        rec = self.env[model].sudo().search(domain, limit=1)
        if rec:
            return rec
        return self.env[model].sudo().create(vals)

    def _ensure_coded_master(self, xmlid, model, code, name, vals):
        """Find company master data by code or name; seed under xmlid only if missing.

        Prefer an already-registered ``tcrm_mock_data`` xmlid, then match existing
        records (e.g. from ``tcrm_propertio`` master XML) by ``code`` / ``name``.
        When creating, register a deterministic xmlid via :meth:`_seed`.
        """
        env = self.env
        rec = env.ref("%s.%s" % (MODULE, xmlid), raise_if_not_found=False)
        if rec:
            return rec
        Model = env[model].sudo()
        company_id = vals.get("company_id")
        domain = []
        if company_id and "company_id" in Model._fields:
            domain.append(("company_id", "=", company_id))
        if code and "code" in Model._fields:
            domain = domain + ["|", ("code", "=", code), ("name", "=", name)]
        else:
            domain = domain + [("name", "=", name)]
        rec = Model.search(domain, limit=1)
        if rec:
            sync = {}
            if code and "code" in Model._fields and rec.code != code:
                sync["code"] = code
            for field in ("sequence", "fold", "color"):
                if field in vals and field in Model._fields and rec[field] != vals[field]:
                    sync[field] = vals[field]
            if sync:
                rec.write(sync)
            return rec
        create_vals = dict(vals, name=name)
        if code and "code" in Model._fields:
            create_vals["code"] = code
        return self._seed(xmlid, model, create_vals)

    def _group_ids(self):
        env = self.env
        gids = [env.ref("base.group_user").id]
        for xid in ("sales_team.group_sale_salesman",
                    "sales_team.group_sale_salesman_all_leads"):
            grp = env.ref(xid, raise_if_not_found=False)
            if grp:
                gids.append(grp.id)
        return [(6, 0, gids)]

    # ------------------------------------------------------------------ builder
    @api.model
    def build_all(self):
        """Entry point. Idempotently builds the whole scenario. Returns a summary."""
        self = self.sudo()
        _logger.info("TCRM Mock Data: starting build_all()")
        reg = {
            "company": self.env.company,
            "currency": self.env.company.currency_id,
            "today": date.today(),
        }
        summary = {}
        summary.update(self._build_teams_and_people(reg))
        summary.update(self._build_partners_and_brokers(reg))
        summary.update(self._build_products(reg))
        summary.update(self._build_crm_master(reg))
        summary.update(self._build_property_inventory(reg))
        summary.update(self._build_crm_pipeline(reg))
        summary.update(self._build_property_transactions(reg))
        summary.update(self._build_sale_orders(reg))
        summary.update(self._build_activities(reg))
        summary.update(self._build_other_apps(reg))
        _logger.info("TCRM Mock Data: build_all() done: %s", summary)
        return summary

    # --- teams & salespeople -------------------------------------------------
    def _build_teams_and_people(self, reg):
        company = reg["company"]
        team = self._seed("team_nova", "crm.team", {
            "name": "Nova Estates Sales",
            "company_id": company.id,
        })
        ayse = self._seed("user_ayse", "res.users", {
            "name": "Ayşe Yılmaz",
            "login": "ayse.nova",
            "email": "ayse.yilmaz@novaestates.com.tr",
            "group_ids": self._group_ids(),
        })
        mehmet = self._seed("user_mehmet", "res.users", {
            "name": "Mehmet Demir",
            "login": "mehmet.nova",
            "email": "mehmet.demir@novaestates.com.tr",
            "group_ids": self._group_ids(),
        })
        for key, user in (("member_ayse", ayse), ("member_mehmet", mehmet)):
            self._seed(key, "crm.team.member", {
                "crm_team_id": team.id,
                "user_id": user.id,
            })
        reg["team"] = team
        reg["ayse"] = ayse
        reg["mehmet"] = mehmet
        return {"teams": 1, "salespeople": 2}

    # --- partners, customers, brokers ---------------------------------------
    def _build_partners_and_brokers(self, reg):
        reg["broker_prime"] = self._seed("broker_prime", "res.partner", {
            "name": "Prime Realty Brokers",
            "is_company": True,
            "email": "contact@primerealty.com.tr",
            "phone": "+90 212 555 0101",
            "city": "Istanbul",
        })
        reg["broker_gold"] = self._seed("broker_gold", "res.partner", {
            "name": "Gold Key Property Agency",
            "is_company": True,
            "email": "info@goldkeyproperty.com.tr",
            "phone": "+90 216 555 0202",
            "city": "Istanbul",
        })
        reg["cust_acme"] = self._seed("cust_acme", "res.partner", {
            "name": "Acme Holding A.Ş.",
            "is_company": True,
            "email": "satin.alma@acmeholding.com.tr",
            "phone": "+90 212 555 0303",
            "city": "Istanbul",
        })
        # (xmlid, name, email, phone, city, partner lead_source)
        specs = [
            ("cust_can", "Can Öztürk", "can.ozturk@gmail.com", "+90 532 555 1001", "Istanbul", "facebook"),
            ("cust_elif", "Elif Kaya", "elif.kaya@hotmail.com", "+90 533 555 1002", "Ankara", "referral"),
            ("cust_deniz", "Deniz Şahin", "deniz.sahin@outlook.com", "+90 534 555 1003", "Izmir", "instagram"),
            ("cust_burak", "Burak Aydın", "burak.aydin@yahoo.com", "+90 535 555 1004", "Bursa", "google_ads"),
            ("prospect_sema", "Sema Arslan", "sema.arslan@gmail.com", "+90 536 555 1005", "Antalya", "whatsapp"),
            ("prospect_omar", "Omar Farouk", "omar.farouk@emirates.net.ae", "+971 50 555 1006", "Dubai", "landline"),
        ]
        customers = {}
        Partner = self.env["res.partner"].sudo()
        has_lead_source = "lead_source" in Partner._fields
        for key, name, email, phone, city, lead_src in specs:
            vals = {
                "name": name,
                "is_company": False,
                "email": email,
                "phone": phone,
                "city": city,
            }
            if has_lead_source:
                vals["lead_source"] = lead_src
            customers[key] = self._seed(key, "res.partner", vals)
            if has_lead_source and customers[key].lead_source != lead_src:
                customers[key].write({"lead_source": lead_src})
        if has_lead_source:
            acme = reg["cust_acme"]
            if acme.lead_source != "sahibinden":
                acme.write({"lead_source": "sahibinden"})
        reg["customers"] = customers
        return {"brokers": 2, "customer_companies": 1, "customers": len(specs)}

    # --- products ------------------------------------------------------------
    def _build_products(self, reg):
        reg["prod_reservation"] = self._seed("product_reservation", "product.template", {
            "name": "Unit Reservation Fee",
            "type": "service",
            "list_price": 5000.0,
        })
        reg["prod_unit"] = self._seed("product_unit_sale", "product.template", {
            "name": "Residential Unit (Property Sale)",
            "type": "service",
            "list_price": 0.0,
        })
        return {"products": 2}

    # --- crm master data -----------------------------------------------------
    def _build_crm_master(self, reg):
        env = self.env
        reg["tag_hot"] = self._get_or_create("crm.tag", [("name", "=", "Sıcak")], {"name": "Sıcak"})
        reg["tag_investor"] = self._get_or_create("crm.tag", [("name", "=", "Yatırımcı")], {"name": "Yatırımcı"})
        # Diverse lead sources (Kaynak) — not all Website
        source_names = {
            "src_website": "Web Sitesi",
            "src_instagram": "Instagram",
            "src_facebook": "Facebook",
            "src_sahibinden": "Sahibinden",
            "src_whatsapp": "WhatsApp",
            "src_landline": "Sabit Hat",
            "src_indoor": "Ofis / Showroom",
            "src_referral": "Referans",
            "src_google": "Google Ads",
        }
        reg["sources"] = {}
        for key, name in source_names.items():
            reg["sources"][key] = self._get_or_create("utm.source", [("name", "=", name)], {"name": name})
        # Back-compat alias used by older seed paths
        reg["source"] = reg["sources"]["src_website"]
        reg["medium_web"] = self._get_or_create("utm.medium", [("name", "=", "Web")], {"name": "Web"})
        reg["medium_social"] = self._get_or_create("utm.medium", [("name", "=", "Sosyal Medya")], {"name": "Sosyal Medya"})
        reg["medium_phone"] = self._get_or_create("utm.medium", [("name", "=", "Telefon")], {"name": "Telefon"})
        reg["medium_portal"] = self._get_or_create("utm.medium", [("name", "=", "İlan Portalı")], {"name": "İlan Portalı"})
        reg["medium_walkin"] = self._get_or_create("utm.medium", [("name", "=", "Ofis")], {"name": "Ofis"})
        reg["medium"] = reg["medium_web"]
        reg["campaign"] = self._get_or_create(
            "utm.campaign",
            [("name", "=", "Nova Bahar Lansmanı")],
            {"name": "Nova Bahar Lansmanı"},
        )
        reg["lost_price"] = self._get_or_create(
            "crm.lost.reason",
            [("name", "=", "Çok pahalı")],
            {"name": "Çok pahalı"},
        )

        stages = env["crm.stage"].sudo().search([], order="sequence, id")
        reg["stage_won"] = (stages.filtered(lambda s: s.is_won)[:1] or stages[-1:])
        reg["stage_new"] = stages[:1]
        reg["stage_qualified"] = stages[1:2] or stages[:1]
        reg["stage_proposition"] = stages[2:3] or stages[-1:]
        return {"crm_tags": 2}

    # --- property inventory --------------------------------------------------
    def _build_property_inventory(self, reg):
        company = reg["company"]
        currency = reg["currency"]

        # Back-compat xmlids from the original Nova scenario.
        self._seed("project_type_res", "propertio.project.type", {
            "name": "Residential", "company_id": company.id})
        self._seed("project_stage_selling", "propertio.project.stage", {
            "name": "Selling", "sequence": 20, "company_id": company.id})

        # Turkish market project types (may already exist from tcrm_propertio master data).
        type_specs = [
            ("ptype_konut", "konut", "Konut Projesi", 10),
            ("ptype_villa", "villa", "Villa Projesi", 20),
            ("ptype_ticari_dukkan", "ticari_dukkan", "Ticari Dükkan Projesi", 30),
            ("ptype_karma", "karma", "Karma Proje", 40),
            ("ptype_devremulk", "devremulk", "Devremülk Projesi", 50),
            ("ptype_arsa_parsel", "arsa_parsel", "Arsa ve Parsel Projesi", 60),
            ("ptype_kentsel_donusum", "kentsel_donusum", "Kentsel Dönüşüm Projesi", 70),
            ("ptype_rezidans", "rezidans", "Rezidans Projesi", 80),
            ("ptype_ofis", "ofis", "Ofis Projesi", 90),
            ("ptype_sanayi_depo", "sanayi_depo", "Sanayi veya Depo Projesi", 100),
        ]
        types = {}
        for xmlid, code, name, seq in type_specs:
            types[code] = self._ensure_coded_master(
                xmlid, "propertio.project.type", code, name,
                {"company_id": company.id, "sequence": seq})

        # Project stages with kanban fold for closed/terminal columns.
        stage_specs = [
            ("pstage_planlama", "planlama", "Planlama", 10, False, 1),
            ("pstage_ruhsat", "ruhsat", "Ruhsat Süreci", 20, False, 2),
            ("pstage_projelendirme", "projelendirme", "Projelendirme", 30, False, 3),
            ("pstage_satisa_hazir", "satisa_hazir", "Satışa Hazır", 40, False, 4),
            ("pstage_on_satista", "on_satista", "Ön Satışta", 50, False, 5),
            ("pstage_insaat_basladi", "insaat_basladi", "İnşaat Başladı", 60, False, 6),
            ("pstage_insaat_devam", "insaat_devam", "İnşaat Devam Ediyor", 70, False, 7),
            ("pstage_teslime_hazir", "teslime_hazir", "Teslime Hazır", 80, False, 8),
            ("pstage_teslim_edildi", "teslim_edildi", "Teslim Edildi", 90, True, 9),
            ("pstage_tamamlandi", "tamamlandi", "Tamamlandı", 100, True, 10),
            ("pstage_durduruldu", "durduruldu", "Durduruldu", 110, True, 11),
            ("pstage_iptal", "iptal", "İptal Edildi", 120, True, 12),
        ]
        stages = {}
        for xmlid, code, name, seq, fold, color in stage_specs:
            stages[code] = self._ensure_coded_master(
                xmlid, "propertio.project.stage", code, name,
                {"company_id": company.id, "sequence": seq, "fold": fold, "color": color})

        cats = {}
        for key, name in (
            ("cat_1p1", "1+1 Apartment"),
            ("cat_2p1", "2+1 Apartment"),
            ("cat_3p1", "3+1 Apartment"),
            ("cat_villa", "Villa"),
            ("cat_dukkan", "Dükkan"),
            ("cat_ofis", "Ofis"),
            ("cat_depo", "Depo"),
            ("cat_arsa", "Arsa / Parsel"),
            ("cat_studio", "Stüdyo"),
        ):
            cats[key] = self._seed(key, "propertio.unit.category", {
                "name": name, "company_id": company.id})
        feats = {}
        for key, name, icon in (
            ("feat_pool", "Swimming Pool", "fa-swimming-pool"),
            ("feat_gym", "Fitness Center", "fa-dumbbell"),
            ("feat_sea", "Sea View", "fa-water"),
            ("feat_parking", "Covered Parking", "fa-car"),
            ("feat_security", "24 Saat Güvenlik", "fa-shield-alt"),
            ("feat_garden", "Peyzaj Bahçe", "fa-tree"),
        ):
            feats[key] = self._seed(key, "propertio.feature", {
                "name": name, "icon": icon, "company_id": company.id})
        status_ready = self._seed("unit_status_ready", "propertio.unit.status", {
            "name": "Ready to Move", "company_id": company.id})
        status_shell = self._seed("unit_status_shell", "propertio.unit.status", {
            "name": "Kaba İnşaat", "company_id": company.id})

        # ---- existing core projects (type/stage refreshed via write) --------
        proj_nova = self._seed("proj_nova_towers", "propertio.project", {
            "name": "Nova Towers", "city": "Istanbul",
            "type_id": types["konut"].id, "stage_id": stages["on_satista"].id,
            "currency_id": currency.id, "gdv": 120000000.0, "company_id": company.id,
            "standard_feature_ids": [(6, 0, [
                feats["feat_pool"].id, feats["feat_gym"].id, feats["feat_parking"].id])],
        })
        proj_nova.write({
            "type_id": types["konut"].id,
            "stage_id": stages["on_satista"].id,
        })
        proj_marina = self._seed("proj_marina", "propertio.project", {
            "name": "Marina Residences", "city": "Izmir",
            "type_id": types["rezidans"].id, "stage_id": stages["insaat_devam"].id,
            "currency_id": currency.id, "gdv": 80000000.0, "company_id": company.id,
            "standard_feature_ids": [(6, 0, [feats["feat_sea"].id, feats["feat_parking"].id])],
        })
        proj_marina.write({
            "type_id": types["rezidans"].id,
            "stage_id": stages["insaat_devam"].id,
        })

        # ---- additional projects: one per type + extra stage coverage -------
        # (xmlid, name, city, type_code, stage_code, gdv, feature_keys)
        project_specs = [
            ("proj_villa_bodrum", "Bodrum Zeytinlik Villaları", "Bodrum",
             "villa", "satisa_hazir", 95000000.0,
             ["feat_pool", "feat_garden", "feat_parking"]),
            ("proj_ticari_bagdat", "Bağdat Caddesi Dükkanları", "Istanbul",
             "ticari_dukkan", "on_satista", 42000000.0,
             ["feat_parking", "feat_security"]),
            ("proj_karma_ankara", "Ankara Merkez Karma Yaşam", "Ankara",
             "karma", "insaat_basladi", 150000000.0,
             ["feat_gym", "feat_parking", "feat_security"]),
            ("proj_devremulk_antalya", "Antalya Sahil Devremülk", "Antalya",
             "devremulk", "teslime_hazir", 28000000.0,
             ["feat_pool", "feat_sea", "feat_parking"]),
            ("proj_arsa_gebze", "Gebze Sanayi Arsa Parselleri", "Kocaeli",
             "arsa_parsel", "planlama", 18000000.0,
             ["feat_security"]),
            ("proj_kentsel_kadikoy", "Kadıköy Kentsel Dönüşüm", "Istanbul",
             "kentsel_donusum", "ruhsat", 67000000.0,
             ["feat_parking", "feat_garden"]),
            ("proj_ofis_maslak", "Maslak Ofis Kuleleri", "Istanbul",
             "ofis", "projelendirme", 210000000.0,
             ["feat_parking", "feat_security", "feat_gym"]),
            ("proj_sanayi_tosb", "TOSB Depo ve Lojistik Kampüsü", "Bursa",
             "sanayi_depo", "teslim_edildi", 55000000.0,
             ["feat_parking", "feat_security"]),
            ("proj_konut_bursa", "Nilüfer Park Konutları", "Bursa",
             "konut", "tamamlandi", 48000000.0,
             ["feat_pool", "feat_garden", "feat_parking"]),
            ("proj_villa_cesme", "Çeşme Alaçatı Villaları", "Izmir",
             "villa", "durduruldu", 36000000.0,
             ["feat_pool", "feat_sea"]),
            ("proj_ticari_bostanci", "Bostancı Plaza Ticari", "Istanbul",
             "ticari_dukkan", "iptal", 22000000.0,
             ["feat_parking"]),
        ]
        projects = {
            "proj_nova_towers": proj_nova,
            "proj_marina": proj_marina,
        }
        for xmlid, name, city, tcode, scode, gdv, feat_keys in project_specs:
            projects[xmlid] = self._seed(xmlid, "propertio.project", {
                "name": name, "city": city,
                "type_id": types[tcode].id, "stage_id": stages[scode].id,
                "currency_id": currency.id, "gdv": gdv, "company_id": company.id,
                "standard_feature_ids": [(6, 0, [feats[k].id for k in feat_keys])],
            })

        # Blocks for core + new projects.
        block_a = self._seed("block_nova_a", "propertio.block", {
            "name": "Block A", "project_id": proj_nova.id})
        block_b = self._seed("block_nova_b", "propertio.block", {
            "name": "Block B", "project_id": proj_nova.id})
        block_c = self._seed("block_marina_c", "propertio.block", {
            "name": "Block C", "project_id": proj_marina.id})
        block_specs = [
            ("block_villa_bodrum_a", "Villa Blok A", "proj_villa_bodrum"),
            ("block_ticari_bagdat_z", "Zemin Hat", "proj_ticari_bagdat"),
            ("block_karma_ankara_a", "A Blok", "proj_karma_ankara"),
            ("block_karma_ankara_b", "B Blok", "proj_karma_ankara"),
            ("block_devremulk_antalya_a", "Sahil Blok", "proj_devremulk_antalya"),
            ("block_arsa_gebze_p", "Parsel Grubu", "proj_arsa_gebze"),
            ("block_kentsel_kadikoy_a", "A Etap", "proj_kentsel_kadikoy"),
            ("block_ofis_maslak_t1", "Kule 1", "proj_ofis_maslak"),
            ("block_sanayi_tosb_d", "Depo Alanı", "proj_sanayi_tosb"),
            ("block_konut_bursa_a", "A Blok", "proj_konut_bursa"),
            ("block_villa_cesme_a", "Villa Sıra", "proj_villa_cesme"),
            ("block_ticari_bostanci_a", "Plaza A", "proj_ticari_bostanci"),
        ]
        blocks = {
            "block_nova_a": block_a,
            "block_nova_b": block_b,
            "block_marina_c": block_c,
        }
        for xmlid, name, proj_key in block_specs:
            blocks[xmlid] = self._seed(xmlid, "propertio.block", {
                "name": name, "project_id": projects[proj_key].id})

        # (xmlid, project, block, num, floor, cat, gross, net, price, view, status)
        unit_specs = [
            ("unit_a101", proj_nova, block_a, "A-101", "1", "cat_1p1", 75, 62, 3200000, "City View", status_ready),
            ("unit_a102", proj_nova, block_a, "A-102", "1", "cat_2p1", 105, 88, 4500000, "City View", status_ready),
            ("unit_a103", proj_nova, block_a, "A-103", "2", "cat_2p1", 105, 88, 4600000, "Garden View", status_ready),
            ("unit_a104", proj_nova, block_a, "A-104", "2", "cat_3p1", 140, 120, 6100000, "Garden View", status_ready),
            ("unit_a105", proj_nova, block_a, "A-105", "3", "cat_3p1", 140, 120, 6300000, "City View", status_ready),
            ("unit_b201", proj_nova, block_b, "B-201", "1", "cat_1p1", 78, 64, 3300000, "Pool View", status_ready),
            ("unit_b202", proj_nova, block_b, "B-202", "2", "cat_2p1", 108, 90, 4700000, "Pool View", status_ready),
            ("unit_b203", proj_nova, block_b, "B-203", "3", "cat_villa", 220, 190, 12500000, "Panoramic", status_ready),
            ("unit_c101", proj_marina, block_c, "C-101", "1", "cat_2p1", 110, 92, 5200000, "Sea View", status_ready),
            ("unit_c102", proj_marina, block_c, "C-102", "2", "cat_3p1", 150, 128, 7400000, "Sea View", status_ready),
            ("unit_c103", proj_marina, block_c, "C-103", "3", "cat_3p1", 150, 128, 7600000, "Sea View", status_shell),
            ("unit_c104", proj_marina, block_c, "C-104", "4", "cat_villa", 240, 205, 14200000, "Sea View", status_shell),
            # Bodrum villas
            ("unit_vb01", projects["proj_villa_bodrum"], blocks["block_villa_bodrum_a"],
             "V-01", "0", "cat_villa", 280, 240, 18500000, "Garden View", status_ready),
            ("unit_vb02", projects["proj_villa_bodrum"], blocks["block_villa_bodrum_a"],
             "V-02", "0", "cat_villa", 310, 265, 21000000, "Pool View", status_ready),
            ("unit_vb03", projects["proj_villa_bodrum"], blocks["block_villa_bodrum_a"],
             "V-03", "0", "cat_villa", 295, 250, 19800000, "Sea View", status_ready),
            # Bağdat shops
            ("unit_bd01", projects["proj_ticari_bagdat"], blocks["block_ticari_bagdat_z"],
             "D-01", "0", "cat_dukkan", 85, 78, 9800000, "Street View", status_ready),
            ("unit_bd02", projects["proj_ticari_bagdat"], blocks["block_ticari_bagdat_z"],
             "D-02", "0", "cat_dukkan", 120, 110, 14500000, "Street View", status_ready),
            ("unit_bd03", projects["proj_ticari_bagdat"], blocks["block_ticari_bagdat_z"],
             "D-03", "1", "cat_dukkan", 95, 88, 11200000, "Avenue View", status_ready),
            # Ankara karma
            ("unit_ka101", projects["proj_karma_ankara"], blocks["block_karma_ankara_a"],
             "KA-101", "1", "cat_2p1", 115, 95, 3900000, "City View", status_shell),
            ("unit_ka102", projects["proj_karma_ankara"], blocks["block_karma_ankara_a"],
             "KA-102", "2", "cat_3p1", 145, 122, 5200000, "Park View", status_shell),
            ("unit_kb01", projects["proj_karma_ankara"], blocks["block_karma_ankara_b"],
             "KB-01", "0", "cat_dukkan", 70, 64, 6100000, "Plaza View", status_shell),
            # Antalya timeshare
            ("unit_da01", projects["proj_devremulk_antalya"], blocks["block_devremulk_antalya_a"],
             "DA-01", "2", "cat_studio", 45, 38, 950000, "Sea View", status_ready),
            ("unit_da02", projects["proj_devremulk_antalya"], blocks["block_devremulk_antalya_a"],
             "DA-02", "3", "cat_1p1", 62, 52, 1250000, "Sea View", status_ready),
            ("unit_da03", projects["proj_devremulk_antalya"], blocks["block_devremulk_antalya_a"],
             "DA-03", "4", "cat_2p1", 88, 74, 1680000, "Garden View", status_ready),
            # Gebze plots
            ("unit_ag01", projects["proj_arsa_gebze"], blocks["block_arsa_gebze_p"],
             "P-01", "0", "cat_arsa", 500, 500, 2500000, "Road Front", status_ready),
            ("unit_ag02", projects["proj_arsa_gebze"], blocks["block_arsa_gebze_p"],
             "P-02", "0", "cat_arsa", 750, 750, 3600000, "Corner Plot", status_ready),
            # Kadıköy urban renewal
            ("unit_kk101", projects["proj_kentsel_kadikoy"], blocks["block_kentsel_kadikoy_a"],
             "KK-101", "1", "cat_2p1", 100, 84, 4800000, "Street View", status_shell),
            ("unit_kk201", projects["proj_kentsel_kadikoy"], blocks["block_kentsel_kadikoy_a"],
             "KK-201", "2", "cat_3p1", 135, 115, 6200000, "Courtyard", status_shell),
            # Maslak offices
            ("unit_om501", projects["proj_ofis_maslak"], blocks["block_ofis_maslak_t1"],
             "OM-501", "5", "cat_ofis", 220, 198, 15500000, "Skyline", status_shell),
            ("unit_om502", projects["proj_ofis_maslak"], blocks["block_ofis_maslak_t1"],
             "OM-502", "5", "cat_ofis", 180, 162, 12800000, "Skyline", status_shell),
            ("unit_om1201", projects["proj_ofis_maslak"], blocks["block_ofis_maslak_t1"],
             "OM-1201", "12", "cat_ofis", 350, 320, 24500000, "Bosphorus View", status_shell),
            # TOSB warehouses
            ("unit_td01", projects["proj_sanayi_tosb"], blocks["block_sanayi_tosb_d"],
             "TD-01", "0", "cat_depo", 1200, 1150, 8900000, "Ramp Access", status_ready),
            ("unit_td02", projects["proj_sanayi_tosb"], blocks["block_sanayi_tosb_d"],
             "TD-02", "0", "cat_depo", 1800, 1720, 12500000, "Dock Access", status_ready),
            # Bursa completed residences
            ("unit_nb101", projects["proj_konut_bursa"], blocks["block_konut_bursa_a"],
             "NB-101", "1", "cat_2p1", 108, 90, 3100000, "Park View", status_ready),
            ("unit_nb102", projects["proj_konut_bursa"], blocks["block_konut_bursa_a"],
             "NB-102", "2", "cat_3p1", 142, 120, 4100000, "Park View", status_ready),
            # Çeşme (suspended) + Bostancı (cancelled) — still show sample inventory
            ("unit_vc01", projects["proj_villa_cesme"], blocks["block_villa_cesme_a"],
             "VC-01", "0", "cat_villa", 260, 220, 16200000, "Sea View", status_ready),
            ("unit_tb01", projects["proj_ticari_bostanci"], blocks["block_ticari_bostanci_a"],
             "TB-01", "0", "cat_dukkan", 90, 82, 7200000, "Plaza View", status_ready),
        ]
        units = {}
        for key, proj, block, num, floor, cat, gross, net, price, view, status in unit_specs:
            units[key] = self._seed(key, "propertio.unit", {
                "name": num, "project_id": proj.id, "block_id": block.id, "floor": floor,
                "category_id": cats[cat].id, "status_id": status.id,
                "gross_m2": gross, "net_m2": net, "list_price": price, "view_type": view,
                "standard_feature_ids": [(6, 0, [feats["feat_parking"].id])],
            })
        # Showcase a handed-over unit on the completed Bursa project (no sale workflow).
        if units["unit_nb102"].state == "available":
            units["unit_nb102"].write({"state": "handover"})

        reg["types"] = types
        reg["stages"] = stages
        reg["proj_nova"] = proj_nova
        reg["proj_marina"] = proj_marina
        reg["projects"] = projects
        reg["units"] = units
        return {
            "projects": len(projects),
            "blocks": len(blocks),
            "units": len(unit_specs),
            "project_types": len(types),
            "project_stages": len(stages),
        }

    # --- crm pipeline --------------------------------------------------------
    def _build_crm_pipeline(self, reg):
        cust = reg["customers"]
        team, ayse, mehmet = reg["team"], reg["ayse"], reg["mehmet"]
        units = reg["units"]
        sources = reg["sources"]
        campaign_id = reg["campaign"].id

        def _channel(src_key, medium_key):
            return {
                "team_id": team.id,
                "source_id": sources[src_key].id,
                "medium_id": reg[medium_key].id,
                "campaign_id": campaign_id,
            }

        projects = reg["projects"]
        # (key, name, partner, project, unit, priority, source_key, medium_key)
        lead_specs = [
            ("lead_web_1", "Web Sitesi — Nova Towers 2+1 talebi", cust["prospect_sema"],
             reg["proj_nova"], None, "2", "src_website", "medium_web"),
            ("lead_ig_1", "Instagram DM — Marina villa seçenekleri", cust["prospect_omar"],
             reg["proj_marina"], None, "3", "src_instagram", "medium_social"),
            ("lead_sh_1", "Sahibinden — Yatırımcı toplu talep", reg["cust_acme"],
             reg["proj_nova"], None, "4", "src_sahibinden", "medium_portal"),
            ("lead_wa_1", "WhatsApp — Nova Towers bilgi", cust["prospect_sema"],
             reg["proj_nova"], None, "2", "src_whatsapp", "medium_social"),
            ("lead_phone_1", "Sabit Hat — Marina 3+1 arayan", cust["prospect_omar"],
             reg["proj_marina"], None, "3", "src_landline", "medium_phone"),
            ("lead_indoor_1", "Ofis / Showroom ziyareti — 1+1", cust["prospect_sema"],
             reg["proj_nova"], None, "2", "src_indoor", "medium_walkin"),
            ("lead_villa_bodrum", "Instagram — Bodrum villa talebi", cust["prospect_omar"],
             projects["proj_villa_bodrum"], None, "4", "src_instagram", "medium_social"),
            ("lead_ticari_bagdat", "Sahibinden — Bağdat Caddesi dükkan", reg["cust_acme"],
             projects["proj_ticari_bagdat"], None, "3", "src_sahibinden", "medium_portal"),
            ("lead_ofis_maslak", "Google Ads — Maslak ofis katı", cust["cust_burak"],
             projects["proj_ofis_maslak"], None, "3", "src_google", "medium_web"),
            ("lead_arsa_gebze", "Web Sitesi — Gebze arsa parseli", cust["cust_deniz"],
             projects["proj_arsa_gebze"], None, "2", "src_website", "medium_web"),
            ("lead_devremulk_antalya", "WhatsApp — Antalya devremülk", cust["prospect_sema"],
             projects["proj_devremulk_antalya"], None, "2", "src_whatsapp", "medium_social"),
            ("lead_karma_ankara", "Referans — Ankara karma proje", cust["cust_elif"],
             projects["proj_karma_ankara"], None, "3", "src_referral", "medium_walkin"),
            ("lead_kentsel_kadikoy", "Ofis — Kadıköy kentsel dönüşüm", cust["cust_can"],
             projects["proj_kentsel_kadikoy"], None, "2", "src_indoor", "medium_walkin"),
            ("lead_sanayi_tosb", "Sabit Hat — TOSB depo yatırımı", reg["cust_acme"],
             projects["proj_sanayi_tosb"], None, "4", "src_landline", "medium_phone"),
        ]
        for key, name, partner, proj, unit, prio, src_key, med_key in lead_specs:
            vals = _channel(src_key, med_key)
            vals.update({
                "name": name, "type": "lead", "partner_id": partner.id,
                "contact_name": partner.name, "email_from": partner.email,
                "user_id": ayse.id, "priority": prio,
                "propertio_project_id": proj.id if proj else False,
                "propertio_unit_id": unit.id if unit else False,
                "tag_ids": [(6, 0, [reg["tag_hot"].id])],
            })
            lead = self._seed(key, "crm.lead", vals)
            # Refresh Kaynak/channel on reseed (seed is otherwise create-only).
            lead.write({
                "name": name,
                "source_id": vals["source_id"],
                "medium_id": vals["medium_id"],
                "campaign_id": vals["campaign_id"],
            })

        # (key, name, partner, user, stage, unit, exp, prob, prio, tags, kind, src_key, med_key)
        opp_specs = [
            ("opp_a101", "Can Öztürk — A-101 satın alma", cust["cust_can"], ayse,
             reg["stage_won"], units["unit_a101"], 3200000, 100, "5", ["tag_hot"], "won",
             "src_facebook", "medium_social"),
            ("opp_a102", "Elif Kaya — A-102 satın alma", cust["cust_elif"], mehmet,
             reg["stage_won"], units["unit_a102"], 4500000, 100, "5", ["tag_hot"], "won",
             "src_referral", "medium_walkin"),
            ("opp_c101", "Acme Holding — C-101 yatırım", reg["cust_acme"], mehmet,
             reg["stage_won"], units["unit_c101"], 5200000, 100, "4", ["tag_investor"], "won",
             "src_sahibinden", "medium_portal"),
            ("opp_a103", "Deniz Şahin — A-103 rezervasyon", cust["cust_deniz"], ayse,
             reg["stage_proposition"], units["unit_a103"], 4600000, 60, "4", ["tag_hot"], "open",
             "src_instagram", "medium_social"),
            ("opp_c102", "Burak Aydın — C-102 ilgi", cust["cust_burak"], ayse,
             reg["stage_qualified"], units["unit_c102"], 7400000, 40, "3", ["tag_investor"], "open",
             "src_google", "medium_web"),
            ("opp_b202", "Sema Arslan — B-202 talep", cust["prospect_sema"], mehmet,
             reg["stage_new"], units["unit_b202"], 4700000, 20, "2", ["tag_hot"], "open",
             "src_whatsapp", "medium_social"),
            ("opp_lost", "Omar Farouk — Villa (kayıp)", cust["prospect_omar"], ayse,
             reg["stage_qualified"], units["unit_b203"], 12500000, 0, "3", ["tag_investor"], "lost",
             "src_landline", "medium_phone"),
            ("opp_vb01", "Omar Farouk — Bodrum V-01 villa", cust["prospect_omar"], mehmet,
             reg["stage_proposition"], units["unit_vb01"], 18500000, 55, "4", ["tag_hot"], "open",
             "src_instagram", "medium_social"),
            ("opp_bd01", "Acme Holding — Bağdat D-01 dükkan", reg["cust_acme"], ayse,
             reg["stage_won"], units["unit_bd01"], 9800000, 100, "5", ["tag_investor"], "won",
             "src_sahibinden", "medium_portal"),
            ("opp_da02", "Sema Arslan — Antalya DA-02", cust["prospect_sema"], ayse,
             reg["stage_qualified"], units["unit_da02"], 1250000, 35, "2", ["tag_hot"], "open",
             "src_whatsapp", "medium_social"),
            ("opp_td01", "Acme Holding — TOSB TD-01 depo", reg["cust_acme"], mehmet,
             reg["stage_won"], units["unit_td01"], 8900000, 100, "4", ["tag_investor"], "won",
             "src_landline", "medium_phone"),
            ("opp_om501", "Burak Aydın — Maslak OM-501 ofis", cust["cust_burak"], mehmet,
             reg["stage_proposition"], units["unit_om501"], 15500000, 50, "3", ["tag_investor"], "open",
             "src_google", "medium_web"),
            ("opp_ag01", "Deniz Şahin — Gebze P-01 arsa", cust["cust_deniz"], ayse,
             reg["stage_new"], units["unit_ag01"], 2500000, 25, "2", ["tag_investor"], "open",
             "src_website", "medium_web"),
        ]
        opps = {}
        for (key, name, partner, user, stage, unit, exp, prob, prio, tags, kind, src_key, med_key) in opp_specs:
            existed = self._exists(key)
            vals = _channel(src_key, med_key)
            vals.update({
                "name": name, "type": "opportunity", "partner_id": partner.id,
                "contact_name": partner.name, "email_from": partner.email,
                "user_id": user.id, "stage_id": stage.id,
                "expected_revenue": exp, "probability": prob, "priority": prio,
                "propertio_project_id": unit.project_id.id, "propertio_unit_id": unit.id,
                "tag_ids": [(6, 0, [reg[t].id for t in tags])],
            })
            opp = self._seed(key, "crm.lead", vals)
            opp.write({
                "name": name,
                "source_id": vals["source_id"],
                "medium_id": vals["medium_id"],
                "campaign_id": vals["campaign_id"],
            })
            if not existed and kind == "lost":
                opp.write({"active": False, "probability": 0,
                           "lost_reason_id": reg["lost_price"].id})
            opps[key] = opp
        reg["opps"] = opps
        return {"leads": len(lead_specs), "opportunities": len(opp_specs)}

    # --- property transactions (offers, sales, installments, payments) -------
    def _build_property_transactions(self, reg):
        today = reg["today"]
        units, cust, opps = reg["units"], reg["customers"], reg["opps"]
        offer_specs = [
            ("offer_a103", units["unit_a103"], cust["cust_deniz"], reg["ayse"], 4600000),
            ("offer_c102", units["unit_c102"], cust["cust_burak"], reg["ayse"], 7300000),
            ("offer_vb01", units["unit_vb01"], cust["prospect_omar"], reg["mehmet"], 18000000),
            ("offer_da02", units["unit_da02"], cust["prospect_sema"], reg["ayse"], 1200000),
            ("offer_om501", units["unit_om501"], cust["cust_burak"], reg["mehmet"], 15000000),
        ]
        for key, unit, partner, user, price in offer_specs:
            self._seed(key, "propertio.offer", {
                "unit_id": unit.id, "partner_id": partner.id, "user_id": user.id,
                "offer_price": price, "date_offer": (today - timedelta(days=10)),
                "date_expiry": (today + timedelta(days=20)),
            })

        sale_specs = [
            ("sale_a101", units["unit_a101"], cust["cust_can"], reg["ayse"],
             reg["broker_prime"], opps["opp_a101"], 3200000, 3),
            ("sale_a102", units["unit_a102"], cust["cust_elif"], reg["mehmet"],
             reg["broker_gold"], opps["opp_a102"], 4500000, 2),
            ("sale_c101", units["unit_c101"], reg["cust_acme"], reg["mehmet"],
             reg["broker_prime"], opps["opp_c101"], 5200000, 1),
            ("sale_bd01", units["unit_bd01"], reg["cust_acme"], reg["ayse"],
             reg["broker_prime"], opps["opp_bd01"], 9800000, 2),
            ("sale_td01", units["unit_td01"], reg["cust_acme"], reg["mehmet"],
             reg["broker_gold"], opps["opp_td01"], 8900000, 4),
        ]
        n_sales = 0
        for (key, unit, partner, user, broker, opp, price, months_ago) in sale_specs:
            existed = self._exists(key)
            contract_date = today - relativedelta(months=months_ago)
            sale = self._seed(key, "propertio.sale", {
                "partner_id": partner.id, "unit_id": unit.id, "opportunity_id": opp.id,
                "agency_id": broker.id, "sales_person_id": user.id, "sale_price": price,
                "date_sale": contract_date, "contract_date": contract_date,
                "currency_id": (unit.currency_id.id or reg["currency"].id),
            })
            if not existed:
                self._build_installments(sale, price, contract_date)
                if sale.state == "draft":
                    sale.action_confirm()
                self._post_payment(sale, contract_date)
            n_sales += 1
        return {"offers": len(offer_specs), "sales": n_sales}

    def _build_installments(self, sale, total, start_date):
        """Create a plan that sums EXACTLY to the sale price (30% down + 12 monthly)."""
        down = round(total * 0.30, 2)
        remaining = round(total - down, 2)
        n = 12
        monthly = round(remaining / n, 2)
        Inst = self.env["propertio.installment"].sudo()
        Inst.create({
            "sale_id": sale.id, "name": "Down Payment", "type": "down_payment",
            "date_due": start_date, "amount": down, "sequence": 1,
        })
        allocated = 0.0
        for i in range(1, n + 1):
            amount = monthly if i < n else round(remaining - allocated, 2)
            allocated = round(allocated + amount, 2)
            Inst.create({
                "sale_id": sale.id, "name": "Installment %s/%s" % (i, n),
                "type": "installment", "date_due": start_date + relativedelta(months=i),
                "amount": amount, "sequence": 1 + i,
            })

    def _post_payment(self, sale, contract_date):
        """Register + post a payment covering down payment + first 2 months via FIFO."""
        installments = sale.installment_ids.sorted("date_due")
        covered = sum(installments[:3].mapped("amount")) if installments else 0.0
        if covered <= 0:
            return
        payment = self.env["propertio.payment"].sudo().create({
            "partner_id": sale.partner_id.id, "sale_id": sale.id, "amount": covered,
            "currency_id": sale.currency_id.id, "exchange_rate": 1.0,
            "payment_method": "bank", "payment_date": contract_date + timedelta(days=3),
        })
        if payment.state == "draft":
            payment.action_post()

    # --- standard sale orders ------------------------------------------------
    def _build_sale_orders(self, reg):
        today = reg["today"]
        cust, opps = reg["customers"], reg["opps"]
        variant_res = reg["prod_reservation"].product_variant_id
        variant_unit = reg["prod_unit"].product_variant_id
        so_specs = [
            ("so_a101", cust["cust_can"], opps["opp_a101"], reg["ayse"], 3200000, "sale"),
            ("so_a103", cust["cust_deniz"], opps["opp_a103"], reg["ayse"], 4600000, "sent"),
            ("so_c102", cust["cust_burak"], opps["opp_c102"], reg["ayse"], 7400000, "draft"),
        ]
        n = 0
        for key, partner, opp, user, price, kind in so_specs:
            existed = self._exists(key)
            so = self._seed(key, "sale.order", {
                "partner_id": partner.id, "opportunity_id": opp.id,
                "team_id": reg["team"].id, "user_id": user.id,
                "date_order": today - timedelta(days=5),
                "order_line": [
                    (0, 0, {"product_id": variant_res.id, "product_uom_qty": 1, "price_unit": 5000}),
                    (0, 0, {"product_id": variant_unit.id,
                            "name": "Unit purchase - %s" % opp.propertio_unit_id.display_name,
                            "product_uom_qty": 1, "price_unit": price}),
                ],
            })
            if not existed:
                if kind == "sale" and so.state in ("draft", "sent"):
                    so.action_confirm()
                elif kind == "sent" and so.state == "draft":
                    so.write({"state": "sent"})
            n += 1
        return {"sale_orders": n}

    # --- activities, meetings, notes ----------------------------------------
    def _build_activities(self, reg):
        env = self.env
        today = reg["today"]
        opps, cust = reg["opps"], reg["customers"]
        call = env.ref("mail.mail_activity_data_call", raise_if_not_found=False)
        meeting = env.ref("mail.mail_activity_data_meeting", raise_if_not_found=False)
        todo = env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        lead_model = env["ir.model"]._get_id("crm.lead")
        n_act = 0
        act_plan = [
            ("act_call_a103", opps["opp_a103"], call, "Call to confirm reservation", 2, reg["ayse"]),
            ("act_todo_c102", opps["opp_c102"], todo, "Send updated payment plan", 4, reg["ayse"]),
            ("act_meet_b202", opps["opp_b202"], meeting, "Site visit at Nova Towers", 7, reg["mehmet"]),
        ]
        for key, opp, atype, summary_txt, days, user in act_plan:
            if not atype:
                continue
            self._seed(key, "mail.activity", {
                "activity_type_id": atype.id, "summary": summary_txt,
                "res_model_id": lead_model, "res_id": opp.id, "user_id": user.id,
                "date_deadline": today + timedelta(days=days),
            })
            n_act += 1

        meet = self._seed("meeting_a103", "calendar.event", {
            "name": "Contract signing - A-103",
            "start": "%s 10:00:00" % (today + timedelta(days=3)),
            "stop": "%s 11:00:00" % (today + timedelta(days=3)),
            "partner_ids": [(6, 0, [cust["cust_deniz"].id])],
            "user_id": reg["ayse"].id,
        })
        n_meet = 1 if meet else 0

        marker = "[TCRM_MOCK_NOTE]"
        for key in ("opp_a103", "opp_c102"):
            opp = opps[key]
            already = opp.message_ids.filtered(lambda m: marker in (m.body or ""))
            if not already:
                opp.message_post(body="%s Mock scenario note: follow up on financing options." % marker)
        return {"activities": n_act, "meetings": n_meet}

    # --- other apps ----------------------------------------------------------
    def _build_other_apps(self, reg):
        env = self.env
        out = {}
        if "tcrm.ai.workspace" in env:
            try:
                ws = self._seed("ai_workspace_nova", "tcrm.ai.workspace", {
                    "name": "Nova Estates Research",
                    "company_id": env.company.id,
                    "owner_id": reg["ayse"].id,
                })
                if "tcrm.ai.conversation" in env:
                    self._seed("ai_conversation_a103", "tcrm.ai.conversation", {
                        "workspace_id": ws.id,
                        "user_id": reg["ayse"].id,
                        "partner_id": reg["customers"]["cust_deniz"].id,
                        "lead_id": reg["opps"]["opp_a103"].id,
                    })
                out["ai_research"] = 1
            except Exception as e:  # non-fatal: schema may vary
                _logger.warning("TCRM Mock Data: skipped AI Research seed: %s", e)
        return out
