Cursor Agent Prompt — TCRM Piyasa Analizi

Fixed instruction

Implement a new TCRM module:

User-facing name: Piyasa Analizi

Technical addon name: tcrm_market_analysis

Do not use Cursor Plan Mode. Do not return multiple plans. Execute this document in order. Inspect the repository before editing and never invent models, fields, XML IDs, routes, commands, database names, services, or test results.

The module must be a production-quality, database-per-tenant real-estate market-intelligence system integrated with the existing TCRM CRM, Property, Sales, Broker, Contacts, Dashboards, and tcrm_master modules.

1. Mandatory source-compliance gate

Do not build or enable an unauthorized screen scraper.

Do not implement:

CAPTCHA bypass;

authentication bypass;

robots.txt bypass;

rate-limit bypass;

rotating proxies to evade blocking;

browser-fingerprint spoofing;

stealth automation;

fake human interaction;

credential theft;

copying or republishing a third-party listing database without permission;

downloading third-party listing images or full descriptions without permission;

collecting private phone numbers, emails, or personal identities without documented authorization.

Data-source priority:

officially authorized API or licensed feed;

tenant-owned corporate listing feed;

approved partner feed;

tenant-uploaded CSV/XLSX/JSON;

tenant-provided exports;

deterministic fictional demo data.

Create a Sahibinden connector adapter only as a disabled integration point. It must refuse to run until valid authorization, permitted API/feed details, credentials, and scope are configured.

Without authorization, finish the complete module using import connectors and demo data. Never automatically fall back to HTML scraping.

2. TCRM multi-tenancy rules

TCRM uses one database per tenant. The existing tcrm_master module is the control plane for tenant identity, tenant domain, database mapping, provisioning, activation, suspension, and administration.

The new module must obey:

tcrm_master remains the only tenant registry and control plane.

Do not create another tenant registry or domain router.

Do not convert the system to shared-schema tenancy.

Do not store tenant market data in the master database.

Install tcrm_market_analysis in tenant databases.

Every listing, snapshot, source, import, job, report, saved analysis, attachment, and metric must exist only in the current tenant database.

Every cron or queue job must target one explicit tenant database.

Never run an import silently across every database.

Never assume record IDs match across databases.

Tenant A must never see Tenant B data, files, jobs, credentials, reports, exports, attachments, or dashboard metrics.

Respect multi-company record rules inside a tenant database.

A client query parameter, cookie, request body, or route parameter must never override the approved domain-to-database mapping.

Business seeding against the master database must be refused.

Before implementation, inspect the actual tcrm_master routing and provisioning code and document it.

3. Anti-hallucination requirements

Before editing, locate:

tcrm_master;

tenant models and fields;

domain-to-database routing;

provisioning flow;

tenant module installation;

Odoo configuration and database filter;

reverse proxy;

TCRM frontend shell and sidebar;

existing Property, CRM, Sales, Broker, Contact, and Dashboard models;

background-job and cron framework;

import conventions;

security conventions;

test and browser-test frameworks;

asset build/update commands.

Do not duplicate an existing model. Extend or reuse it.

Do not claim anything passed unless it was executed successfully. Every completed task must include exact file paths, commands, output, and test evidence.

4. Product goal

Piyasa Analizi must answer:

listing inventory by location and category;

median and mean asking price;

asking price per square metre;

price and inventory trends;

listing age and estimated days on market;

comparable listings for a TCRM unit;

price position of a project/unit against comparables;

sale-versus-rent market relationship;

indicative gross rental yield;

outliers, duplicates, and data-quality problems;

geographic and category performance;

source and import health.

Always label asking prices as asking prices, not completed transaction prices. A removed listing must not automatically be marked as sold.

Required execution phases

Execute exactly:

Repository and tenancy audit

Existing model inventory

Source-compliance architecture

Module skeleton

Security and isolation

Normalized market-data model

Connector framework

Import pipeline

Snapshot/history engine

Analytics engine

TCRM integrations

Premium user interface

Dashboards

Tenant-isolated demo data

Backend tests

Tenant-isolation tests

Connector/import tests

Analytics validation

HTTP/JSON-RPC tests

Browser tests

Performance/operations

Final report

Do not skip phase gates.

Phase 1 — Repository and tenancy audit

Create:

docs/execution/tcrm_market_analysis_inventory.md

Document:

repository structure;

Git status and branch;

custom addons;

exact tcrm_master path;

tenant model names;

domain and database fields;

domain-to-database request flow;

provisioning and suspension flow;

module-installation flow;

relevant TCRM models;

queue/cron/import frameworks;

test commands;

asset commands;

module update commands;

unresolved facts.

Do not write module code before this document exists.

Phase 2 — Existing model inventory

Create:

docs/execution/tcrm_market_analysis_model_map.md

Find existing models for:

property project;

building/block/tower/floor;

property unit and unit type;

geographic location;

broker/agency;

owner/contact;

lead/opportunity;

quotation/sale;

reservation;

payment plan/installment;

valuation/comparables;

external listing;

import job;

dashboard metric.

For each concept record:

exact model;

addon;

reusable fields;

missing fields;

relationship to the new module.

Phase 3 — Source architecture

Build source adapters for authorized:

REST;

SOAP;

JSON;

XML;

SFTP;

CSV;

XLSX;

uploaded JSON;

tenant-owned exports;

fictional demo generator.

Every source must expose:

authorization status;

enabled/disabled;

source type;

capability flags;

last successful run;

last error;

rate-limit state;

retention policy;

data mapping version.

Capability flags may include:

taxonomy;

listing search;

details;

pagination;

incremental synchronization;

seller type;

organization;

coordinates;

images;

history;

removed-listing detection.

Every imported value must preserve provenance:

tenant database;

source;

external ID;

permitted source URL;

job;

observed time;

imported time;

raw payload checksum;

parser version;

mapping version;

quality status.

Phase 4 — Addon skeleton

Create addon tcrm_market_analysis using repository conventions for manifest, dependencies, security, menus, actions, views, controllers, OWL/JavaScript, assets, tests, translations, and demo data.

Add TCRM sidebar app:

Piyasa Analizi

Suggested route:

/tcrm/market-analysis

Use a different route only when required by the existing TCRM shell.

Use an original TCRM icon. Do not copy third-party logos, CSS, HTML, trade dress, or visual assets.

Sections:

Genel Bakış

Piyasa Gezgini

Harita

Emsal Analizi

Trendler

Stok/Envanter

Kaydedilmiş Analizler

Raporlar

Veri Kaynakları

İçe Aktarımlar

Senkronizasyon İşleri

Veri Kalitesi

Ayarlar

Phase 5 — Security

Use existing TCRM groups where possible. Otherwise add minimal roles:

Market Analysis Viewer

Market Analyst

Market Data Manager

Market Analysis Administrator

Requirements:

viewers read approved data;

analysts save analyses and comparable sets;

managers configure mappings and imports;

administrators configure source/retention settings;

credentials never appear in list views, logs, exports, JSON-RPC, or client payloads;

raw payload access is restricted;

company record rules are enforced;

master users do not automatically receive tenant market access.

Add negative tests for unauthorized source access, import files, reports, exports, credentials, database switching, and cross-tenant access.

Phase 6 — Normalized data model

Reuse existing models first. Suggested missing models:

tcrm.market.source

Fields:

name;

source type;

state;

authorization state;

active;

company scope;

secure credential reference;

capabilities;

limits;

retention;

last success;

last failure;

health.

tcrm.market.import.job

Track:

source;

explicit tenant context;

requester;

start/end;

state;

input filename/checksum;

read/created/updated/skipped/rejected counts;

warnings;

error summary;

parser/mapping versions;

retry count.

tcrm.market.listing

Normalized listing identity:

source;

external listing ID;

permitted source URL;

first/last observed;

source listing date;

active/removed/expired state;

transaction type;

normalized category hierarchy;

short title where permitted;

location;

source location text;

coordinates where permitted;

currency;

asking price;

gross/net area;

gross/net price per square metre;

rooms;

bedrooms;

bathrooms;

building age;

floor/total floors;

heating;

kitchen;

balcony;

elevator;

parking;

furnished;

use status;

site/compound;

mortgage eligibility;

title-deed status;

exchange/swap;

seller type;

permitted organization reference;

media count;

quality score;

duplicate cluster;

source checksum.

Do not store private contact data by default. Do not store full copyrighted descriptions or images without license.

tcrm.market.listing.snapshot

Track each observation:

listing;

observed at;

asking price;

currency;

normalized price;

state;

mutable fields;

checksum;

import job;

change flags.

Never overwrite historical prices.

tcrm.market.seller

For authorized organization-level analysis:

seller type;

source-local stable identifier;

licensed business display name;

coverage;

active count;

first/last observed.

Use pseudonymous identifiers for individual sellers.

Mapping models

Map source values to normalized:

transaction;

category/subcategory;

province/district/neighborhood;

currency;

room type;

heating;

building age;

use status;

title deed;

seller type;

amenities.

tcrm.market.analysis

Store user/company, name, description, filters, dates, metrics, visibility, sharing, scheduled report settings, and last calculation.

Comparable models

tcrm.market.comparable.set

tcrm.market.comparable.line

Link to existing TCRM project, unit, opportunity, quotation, sale, and valuation models where available.

Phase 7 — Connector framework

Implement repository-consistent equivalents of:

validate configuration;

test connection;

fetch taxonomy;

fetch page;

fetch authorized detail;

normalize;

return next cursor;

report authorization failure;

report rate limit;

report permanent failure.

Controls:

explicit enable;

explicit tenant database;

timeout;

bounded retries;

exponential backoff;

maximum pages;

maximum records;

concurrency limit;

rate limit;

kill switch;

dry run;

audit log.

Sahibinden adapter:

disabled by default;

requires authorization evidence and approved endpoint/feed;

refuses unauthorized execution;

never falls back to page scraping;

never bypasses controls;

never logs credentials.

Phase 8 — Import pipeline

Implement:

receive authorized feed or uploaded file;

validate type/schema;

calculate checksum;

create job;

parse;

map taxonomy;

validate;

normalize numbers/currency/units/location;

preview;

detect external identity;

create/update listing;

create changed snapshot;

detect duplicates;

calculate derived metrics;

collect row warnings;

commit safely in batches;

produce summary;

expose rejected rows safely.

Preview must show total, valid, invalid, unmapped category/location, missing fields, duplicates, and sample normalized records.

Re-importing unchanged data must not create duplicates or redundant snapshots.

Phase 9 — History and lifecycle

Implement:

first and last observed;

price changes;

attribute changes;

active/inactive/removed;

listing age;

days on market;

reactivation;

repost/duplicate detection;

stale handling;

retention.

Do not infer “sold” from disappearance. Use removed_from_source unless explicit licensed source data proves a transaction.

Phase 10 — Analytics

Metrics:

active/new/removed count;

median/mean/min/max asking price;

10th/25th/75th/90th percentiles;

median gross/net price per square metre;

listing age;

median days on market;

price-change rate and amount;

inventory trend;

new-to-removed ratio;

category/room/building-age mix;

seller-type mix where allowed;

sale-to-rent asking ratio;

indicative gross rental yield;

geographic distribution;

data completeness;

outliers;

duplicates.

Time grains:

week;

month;

quarter;

year;

custom.

Comparable ranking must be explainable using factors such as transaction, category, neighborhood/proximity, area, rooms, age, floor, amenities, freshness, active state, and quality.

For a selected unit show:

subject asking price;

subject price/m²;

comparable median/range;

percentile;

estimated reasonable asking range;

confidence;

sample size;

filters;

excluded outliers;

analysis date.

Label outputs as estimates, not guaranteed valuations.

Phase 11 — TCRM integration

CRM

From an opportunity:

open market analysis with prefilled location/category/budget;

save and attach analysis;

create comparable set;

store summary;

do not create contacts from unauthorized source data.

Property

From project/unit:

prefill attributes;

compare with market;

attach approved comparables;

show price-position indicator;

show date and sample size.

Sales

From quotation/sale:

show market context;

attach an internal analysis report;

preserve the analysis snapshot used during pricing;

never change contractual prices automatically.

Brokers/Contacts

Allow manual confirmed linking of an authorized organization-level market seller to a TCRM broker/agency. Preserve provenance. Do not auto-create contacts from private listing data.

Dashboards

Use the existing TCRM dashboard system. Do not build a parallel dashboard platform. All queries must remain tenant-local.

Phase 12 — Premium UI

Overview

Show:

active/new/removed;

median asking price;

median price/m²;

median listing age;

price trend;

inventory trend;

freshness;

source health;

data quality.

Market Explorer filters

Support dynamically mapped fields.

Transaction:

sale;

rent;

short-term rent where available.

Categories:

residential;

commercial/workplace;

land;

building;

tourism;

time-share;

other mapped categories.

Residential subcategories where supplied:

apartment;

residence;

detached house;

villa;

farm house;

mansion;

waterside residence;

waterside apartment;

summer house;

cooperative.

Location:

country;

province;

district;

neighborhood;

map bounds/radius where coordinates exist.

Price:

currency;

min/max asking price;

normalized currency;

min/max price/m².

Physical:

gross/net area;

rooms;

bedrooms;

bathrooms;

building age;

floor;

total floors;

heating;

kitchen;

balcony;

elevator;

parking;

furnished;

use status;

compound/site;

mortgage eligibility;

title deed;

exchange;

listing date;

seller type;

media availability;

keywords.

Quality/source:

source;

state;

observed dates;

quality score;

duplicate;

outlier.

Results:

table;

cards;

map;

configurable columns;

sort;

pagination;

saved filters;

comparison basket;

authorized export;

provenance;

freshness;

quality warning.

Map

Use the approved existing map provider:

clusters;

heatmap;

bounds;

radius/polygon where supported;

median price;

price/m²;

count;

category layer.

Comparable workspace

Show:

subject property;

comparables;

map;

distributions;

price/m² chart;

include/exclude controls;

explanation;

summary;

save;

attach to TCRM records;

internal report.

Data Sources and Imports

Show authorization state, health, last/next run, counts, warnings, failures, test connection, upload, preview, run, retry, cancel where supported, rejected rows, and audit history. Never display secrets.

Phase 13 — Dashboards

Add to the existing TCRM dashboard system:

KPI cards;

price trend;

price/m² trend;

inventory trend;

new vs removed;

price distributions;

listing-age distribution;

categories;

rooms;

geographic rankings;

heatmap;

quality;

source health;

import volume.

Charts should drill into Market Explorer where practical.

When no authorized data exists, show “No authorized market data loaded,” not fake zero charts.

Phase 14 — Demo data

Create deterministic fictional demo data for at least two isolated tenant databases.

Example:

Tenant A: İstanbul apartment/office market.

Tenant B: Ankara and İzmir apartment/villa/commercial market.

Include:

sale/rent;

currencies;

locations;

categories;

price changes;

removed listings;

duplicates;

outliers;

agencies;

pseudonymous private sellers;

comparable sets;

saved analyses;

CRM links;

property links;

sales links;

dashboards.

Do not copy real descriptions, images, contacts, or protected source content.

Seeding must be idempotent.

Tenant A seed must not change Tenant B. Master database seed must be refused.

Phase 15 — Backend tests

Test:

installation;

ACLs and record rules;

secret protection;

input validation;

mapping;

numeric/currency/unit/location normalization;

listing upsert;

snapshots;

changes;

removed state;

duplicates;

idempotency;

saved analyses;

comparable ranking;

medians/percentiles;

price/m²;

yield;

TCRM relationships;

reports;

cron and explicit database safety;

refusal to seed master.

Never use live third-party websites in automated tests.

Phase 16 — Isolation tests

Use master, Tenant A, and Tenant B.

Prove isolation of:

sources;

credentials;

files;

jobs;

listings;

snapshots;

sellers;

analyses;

reports;

attachments;

exports;

dashboards;

queue jobs;

cron jobs;

JSON-RPC;

browser sessions.

Test forged database parameters and direct cross-tenant URLs.

Any leak blocks completion.

Phase 17 — Import tests

Use fixture connectors and files.

Test:

success;

invalid credentials;

unauthorized connector;

timeout;

rate limit;

malformed response;

optional missing fields;

pagination;

incremental cursor;

retry;

kill switch;

max pages;

dry run;

CSV/XLSX/JSON;

duplicate file/row;

unmapped values;

partial failure;

safe transaction behavior.

Do not test against live Sahibinden pages.

Phase 18 — Analytics validation

Use known datasets and assert exact results for:

median;

mean;

percentiles;

gross/net price/m²;

price changes;

listing age;

inventory;

geography;

sale/rent ratio;

gross yield;

comparable order;

outliers;

currency;

empty data;

one record;

missing values.

Phase 19 — HTTP and JSON-RPC

For each tenant test:

module entry;

Overview;

Explorer;

Map;

Comparables;

Trends;

Sources;

Imports;

Jobs;

saved analysis;

dashboard drill-down.

HTTP 200 is insufficient. Verify expected tenant markers, authenticated state, no login/database selector, no traceback, no access error, no master content, no other-tenant data, and no secret exposure.

JSON-RPC must verify tenant-local counts, metrics, analyses, TCRM links, and marker records.

Phase 20 — Browser tests

For both tenants:

open domain;

authenticate;

open Piyasa Analizi;

verify icon;

verify Overview;

apply geographic/category/transaction/price/area filters;

switch table/cards/map;

save analysis;

create comparable set;

open from Property;

open from CRM;

open from Sales;

test dashboard drill-down;

test import preview;

verify unauthorized source refuses to run;

verify no console exceptions;

verify no critical failed requests;

verify no other-tenant content.

Capture screenshots where supported.

Phase 21 — Performance and operations

Requirements:

indexed paginated queries;

bounded map results/aggregation;

bounded imports;

no N+1 loops;

background jobs for heavy work;

retention/archival for snapshots;

bounded raw payload storage;

query-plan review;

source and tenant kill switches;

pause/resume;

retry/cancel where supported;

health;

structured logs;

deletion/retention;

migration and backup compatibility.

Review indexes for source/external ID, state, category, transaction, geography, price, price/m², observation date, duplicate cluster, and analysis ownership.

Phase 22 — Final report

Create:

docs/execution/tcrm_market_analysis_final_report.md

Include:

summary;

exact module path;

architecture;

tenancy;

tcrm_master integration;

compliance design;

connectors;

data model;

TCRM integrations;

UI;

formulas;

security;

modified/new files;

migrations/indexes;

demo data;

exact commands;

installation/update/seed commands;

backend results;

isolation results;

import results;

analytics results;

HTTP/JSON-RPC results;

browser results;

performance;

limitations;

blocked items;

exact requirements to enable an authorized Sahibinden connector;

Git diff summary.

Never claim the Sahibinden integration is live unless authorized access was configured and actually tested.

Definition of done

Complete only when:

addon installs;

sidebar and screens work;

tcrm_master remains control plane;

market data exists only in tenant databases;

no cross-tenant access exists;

master contains no business market data;

jobs target one database;

no CAPTCHA/rate-limit/access-control bypass exists;

no unauthorized scraper is active;

Sahibinden adapter remains disabled without authorization;

imports and demo data work;

provenance and history work;

CRM/Property/Sales/Dashboard integrations work;

metrics are tested and explainable;

asking prices are correctly labeled;

removed listings are not falsely called sold;

demo data is isolated and idempotent;

backend, isolation, import, analytics, HTTP/JSON-RPC, and browser tests pass;

final report contains actual evidence.

Immediate instruction

Start with Phase 1.

Do not enter Plan Mode.Do not write live scraper code.Create docs/execution/tcrm_market_analysis_inventory.md first.

After every phase:

update execution documentation;

list changed files;

run relevant tests;

include actual output;

fix failures before continuing;

do not commit unless the user explicitly asks.