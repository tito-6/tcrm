# -*- coding: utf-8 -*-
# Part of TCRM. See LICENSE file for full copyright and licensing details.
"""Import pipeline for authorized uploads / feeds."""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from tcrm import fields

from .normalization import normalize_raw_row
from .tenant_guard import assert_listing_write_allowed

_logger = logging.getLogger(__name__)


def _payload_checksum(raw: dict) -> str:
    blob = json.dumps(raw, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def file_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_listing_date(value):
    """Accept ISO or TR dd-mm-yyyy / dd.mm.yyyy; return date or None."""
    from datetime import datetime
    if not value:
        return None
    if hasattr(value, "year"):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


class ImportPipeline:
    PARSER_VERSION = "1.0.0"
    MAPPING_VERSION = "1.0.0"

    def __init__(self, env, source, job, *, dry_run: bool = False, company_id: Optional[int] = None):
        self.env = env
        self.source = source
        self.job = job
        self.dry_run = dry_run
        self.company_id = company_id or env.company.id
        self.warnings: List[str] = []
        self.rejected: List[Dict[str, Any]] = []
        self.preview_samples: List[Dict[str, Any]] = []
        self.counts = {
            "read": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "rejected": 0,
            "snapshots": 0,
        }

    def _mapping_get(self, map_type: str, source_value: str):
        Map = self.env["tcrm.market.mapping"]
        rec = Map.search([
            ("company_id", "=", self.company_id),
            ("map_type", "=", map_type),
            ("source_value", "=", str(source_value)),
            ("active", "=", True),
        ], limit=1)
        return rec.target_value if rec else False

    def preview(self, rows: List[dict]) -> dict:
        valid = invalid = unmapped_cat = unmapped_loc = missing = dup = 0
        samples = []
        seen = set()
        for raw in rows:
            vals, warns = normalize_raw_row(raw, mapping_get=self._mapping_get)
            self.counts["read"] += 1
            ext = vals.get("external_listing_id")
            if not ext or "missing_asking_price" in warns:
                invalid += 1
            else:
                valid += 1
            if any(w.startswith("unmapped_category") for w in warns):
                unmapped_cat += 1
            if "missing_location" in warns:
                unmapped_loc += 1
                missing += 1
            if ext and ext in seen:
                dup += 1
            if ext:
                seen.add(ext)
            if len(samples) < 10:
                samples.append({k: vals[k] for k in (
                    "external_listing_id", "transaction_type", "category_code",
                    "province", "district", "asking_price", "gross_area", "currency_name",
                ) if k in vals})
        return {
            "total": len(rows),
            "valid": valid,
            "invalid": invalid,
            "unmapped_category": unmapped_cat,
            "unmapped_location": unmapped_loc,
            "missing_fields": missing,
            "duplicates_in_file": dup,
            "sample_normalized": samples,
            "parser_version": self.PARSER_VERSION,
            "mapping_version": self.MAPPING_VERSION,
        }

    def run(self, rows: List[dict], *, batch_size: int = 100) -> dict:
        assert_listing_write_allowed(self.env)
        Listing = self.env["tcrm.market.listing"]
        Snapshot = self.env["tcrm.market.listing.snapshot"]
        Seller = self.env["tcrm.market.seller"]
        now = fields.Datetime.now()
        dbname = self.env.cr.dbname

        self.job.write({
            "state": "running",
            "date_start": now,
            "tenant_db_name": dbname,
            "parser_version": self.PARSER_VERSION,
            "mapping_version": self.MAPPING_VERSION,
        })

        if self.dry_run:
            preview = self.preview(rows)
            self.job.write({
                "state": "done",
                "date_end": fields.Datetime.now(),
                "count_read": preview["total"],
                "count_skipped": preview["total"],
                "warning_summary": "dry_run",
                "preview_json": json.dumps(preview, default=str),
            })
            return preview

        for idx, raw in enumerate(rows):
            self.counts["read"] += 1
            vals, warns = normalize_raw_row(raw, mapping_get=self._mapping_get)
            ext = vals.get("external_listing_id")
            if not ext:
                self.counts["rejected"] += 1
                self.rejected.append({"row": idx, "reason": "missing_external_id"})
                continue

            checksum = _payload_checksum(raw)
            seller = False
            if vals.get("seller_external_id") or vals.get("organization_name"):
                seller = Seller._upsert_from_import(
                    company_id=self.company_id,
                    source=self.source,
                    external_id=vals.get("seller_external_id") or vals.get("organization_name"),
                    seller_type=vals.get("seller_type") or "unknown",
                    display_name=vals.get("organization_name") or False,
                )

            url = vals.get("permitted_source_url") or False
            existing = Listing.search([
                ("company_id", "=", self.company_id),
                ("source_id", "=", self.source.id),
                ("external_listing_id", "=", ext),
            ], limit=1)
            if not existing and url:
                existing = Listing.search([
                    ("company_id", "=", self.company_id),
                    ("source_id", "=", self.source.id),
                    ("permitted_source_url", "=", url),
                ], limit=1)

            image_urls = vals.get("image_urls") or []
            if isinstance(image_urls, str):
                try:
                    image_urls = json.loads(image_urls)
                except json.JSONDecodeError:
                    image_urls = [image_urls]

            listing_vals = {
                "company_id": self.company_id,
                "source_id": self.source.id,
                "external_listing_id": ext,
                "permitted_source_url": vals.get("permitted_source_url") or False,
                "transaction_type": vals["transaction_type"],
                "category_code": vals["category_code"],
                "subcategory_code": vals.get("subcategory_code") or False,
                "title": vals.get("title") or False,
                "province": vals.get("province") or False,
                "district": vals.get("district") or False,
                "neighborhood": vals.get("neighborhood") or False,
                "source_location_text": vals.get("source_location_text") or False,
                "latitude": vals.get("latitude") or False,
                "longitude": vals.get("longitude") or False,
                "currency_name": vals.get("currency_name") or "TRY",
                "asking_price": vals.get("asking_price") or 0.0,
                "gross_area": vals.get("gross_area") or False,
                "net_area": vals.get("net_area") or False,
                "gross_price_m2": vals.get("gross_price_m2") or False,
                "net_price_m2": vals.get("net_price_m2") or False,
                "rooms": vals.get("rooms") or False,
                "bedrooms": vals.get("bedrooms") or False,
                "bathrooms": vals.get("bathrooms") or False,
                "building_age": vals.get("building_age") or False,
                "floor": vals.get("floor") or False,
                "total_floors": vals.get("total_floors") or False,
                "heating": vals.get("heating") or False,
                "kitchen": vals.get("kitchen") or False,
                "balcony": vals.get("balcony") or False,
                "elevator": vals.get("elevator") or False,
                "parking": vals.get("parking") or False,
                "furnished": vals.get("furnished") or False,
                "use_status": vals.get("use_status") or False,
                "in_compound": vals.get("in_compound") or False,
                "mortgage_eligible": vals.get("mortgage_eligible") or False,
                "title_deed_status": vals.get("title_deed_status") or False,
                "exchange_possible": vals.get("exchange_possible") or False,
                "seller_type": vals.get("seller_type") or "unknown",
                "seller_id": seller.id if seller else False,
                "media_count": vals.get("media_count") or len(image_urls) or 0,
                "image_urls_json": json.dumps(image_urls, ensure_ascii=False) if image_urls else False,
                "last_observed_at": now,
                "state": "active",
                "source_checksum": checksum,
                "import_job_id": self.job.id,
                "quality_status": "warning" if warns else "ok",
                "quality_notes": ", ".join(warns) if warns else False,
                "parser_version": self.PARSER_VERSION,
                "mapping_version": self.MAPPING_VERSION,
                "tenant_db_name": dbname,
            }
            listing_date = vals.get("source_listing_date")
            if listing_date:
                parsed = _parse_listing_date(listing_date)
                if parsed:
                    listing_vals["source_listing_date"] = parsed
                else:
                    # Keep raw text in location notes path via quality notes
                    notes = listing_vals.get("quality_notes") or ""
                    listing_vals["quality_notes"] = ((notes + ", ") if notes else "") + "listing_date:%s" % listing_date

            changed = True
            if existing:
                if existing.source_checksum == checksum:
                    self.counts["skipped"] += 1
                    changed = False
                    existing.write({
                        "last_observed_at": now,
                        "import_job_id": self.job.id,
                        "state": "active",
                    })
                else:
                    # Detect price change before write
                    price_changed = abs((existing.asking_price or 0) - (listing_vals["asking_price"] or 0)) > 0.0001
                    listing_vals["first_observed_at"] = existing.first_observed_at or now
                    existing.write(listing_vals)
                    self.counts["updated"] += 1
                    if price_changed:
                        listing_vals["_price_changed"] = True
                    listing = existing
            else:
                listing_vals["first_observed_at"] = now
                listing = Listing.create(listing_vals)
                self.counts["created"] += 1

            if changed:
                Snapshot.create({
                    "listing_id": listing.id,
                    "company_id": self.company_id,
                    "observed_at": now,
                    "asking_price": listing.asking_price,
                    "currency_name": listing.currency_name,
                    "gross_area": listing.gross_area,
                    "net_area": listing.net_area,
                    "gross_price_m2": listing.gross_price_m2,
                    "state": listing.state,
                    "checksum": checksum,
                    "import_job_id": self.job.id,
                    "change_flags": "created" if not existing else "updated",
                    "mutable_json": json.dumps({
                        "rooms": listing.rooms,
                        "floor": listing.floor,
                        "building_age": listing.building_age,
                    }, default=str),
                })
                self.counts["snapshots"] += 1

            if warns:
                self.warnings.extend(warns)

            if batch_size and (idx + 1) % batch_size == 0:
                # Flush ORM cache in batches; avoid cr.commit() so tests and
                # outer transactions remain safe. Operators may wrap large
                # imports in an explicit DB cursor strategy outside tests.
                self.env.flush_all()

        # Duplicate clustering (same company, similar price/area/location)
        Listing._recompute_duplicate_clusters(company_id=self.company_id)

        summary = dict(self.counts)
        summary["warnings"] = sorted(set(self.warnings))[:50]
        summary["rejected_sample"] = self.rejected[:20]
        self.job.write({
            "state": "done",
            "date_end": fields.Datetime.now(),
            "count_read": self.counts["read"],
            "count_created": self.counts["created"],
            "count_updated": self.counts["updated"],
            "count_skipped": self.counts["skipped"],
            "count_rejected": self.counts["rejected"],
            "warning_summary": "\n".join(summary["warnings"][:30]),
            "error_summary": False,
            "preview_json": json.dumps({"rejected": self.rejected[:50]}, default=str),
        })
        self.source.write({
            "last_success_at": fields.Datetime.now(),
            "last_error": False,
            "health": "healthy",
            "rate_limit_state": "ok",
        })
        return summary
