# TCRM Public Documentation Research, Information Architecture, and Cursor Build Prompt

**Target public route:** `https://tcrm.online/Documentations`  
**Recommended aliases:** `/documentations`, `/documentation`, `/docs` → permanent redirect to `/Documentations`  
**Platform version researched:** upstream 19.0 documentation structure  
**Document purpose:** research blueprint, page inventory, content rules, implementation specification, and a production-ready Cursor Agent prompt.

---

## 1. Important legal and content boundary

The upstream documentation source repository is published under **Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0)**. That license permits reuse and adaptation, but copied or adapted text requires attribution, a license link, an indication of changes, and ShareAlike distribution.

Therefore, TCRM has two lawful implementation options:

### Option A — Original TCRM documentation, recommended

Use the upstream documentation only as a research checklist for concepts and workflows.

- Do not copy paragraphs.
- Do not copy screenshots, diagrams, icons, logos, CSS, HTML, page templates, or source files.
- Do not mechanically replace upstream brand names with “TCRM.”
- Inspect the real TCRM interface and source code.
- Write every page in original TCRM wording.
- Capture fresh screenshots from a TCRM staging tenant.
- Document only features that actually exist in TCRM.
- Public pages may contain only TCRM branding.
- No upstream attribution is required for independently written text that does not reuse protected expression.

### Option B — Adapted upstream documentation

If text, images, diagrams, examples, or substantial page content are adapted, the public documentation must provide the attribution and ShareAlike notices required by CC BY-SA 4.0. This option conflicts with the requirement to remove every upstream reference.

**This blueprint uses Option A. It is not a verbatim documentation mirror or a content-stripping workflow.**

---

## 2. Research summary

The official 19.0 documentation is organized into these major areas:

1. User documentation
   - Essentials
   - Finance
   - Sales
   - Websites
   - Supply Chain
   - Human Resources
   - Marketing
   - Services
   - Productivity
   - Studio
   - General Settings
2. Database administration
3. Developer tutorials
4. Developer how-to guides
5. Developer reference
6. Contribution guidance
7. Legal and subscription material

TCRM should not mirror this structure blindly. It should use it as a coverage checklist, then document the actual TCRM product:

- database-per-tenant SaaS behavior;
- TCRM Master control plane;
- CRM and Lead Havuzu;
- Sales;
- Propertio and project stock tracking;
- Contacts;
- Messaging;
- Calendar and activities;
- To-Do;
- Projects;
- Invoicing and payments;
- Marketing Hub;
- Santral;
- TCRM AI;
- dashboards and reports;
- users, companies, roles, tenant entitlements, and integrations.

---

## 3. Scope rules

A page is eligible for publication only when all of the following are true:

1. The feature exists in the current TCRM source or an approved release branch.
2. The feature is installed or provisionable in at least one supported TCRM plan.
3. The page can be verified against a staging tenant.
4. The wording and screenshots are original TCRM materials.
5. The feature is not merely described by upstream premium documentation without a corresponding TCRM implementation.
6. Security-sensitive administrator procedures are reviewed before publication.
7. Tenant-specific credentials, database names, API keys, internal URLs, IP addresses, and customer data are excluded.

### Do not publish upstream-only material

Exclude these upstream sections unless TCRM has an independently implemented equivalent that is documented entirely from TCRM behavior:

- Studio;
- proprietary document management;
- proprietary e-signature;
- proprietary spreadsheet and dashboard applications;
- proprietary knowledge-base application;
- planning;
- field service;
- helpdesk;
- appraisals;
- front desk;
- referrals;
- proprietary payroll features;
- social marketing;
- marketing automation;
- IoT;
- hosted-cloud-specific administration;
- commercial subscription, support, partnership, and enterprise-upgrade documentation;
- proprietary connectors or services not shipped by TCRM.

### Mixed-feature sections

The following areas contain both broadly available concepts and edition-specific functionality. Include only verified TCRM behavior:

- accounting;
- payment providers;
- barcode;
- quality;
- maintenance;
- product lifecycle management;
- subscriptions;
- rental;
- appointments;
- data cleaning;
- WhatsApp;
- telephony;
- AI;
- advanced dashboards;
- advanced reporting.

---

## 4. Public documentation URL architecture

Use a stable, versioned, SEO-friendly hierarchy.

```text
/Documentations
/Documentations/getting-started
/Documentations/core
/Documentations/crm
/Documentations/sales
/Documentations/contacts
/Documentations/propertio
/Documentations/calendar
/Documentations/todo
/Documentations/messaging
/Documentations/projects
/Documentations/invoicing
/Documentations/marketing-hub
/Documentations/santral
/Documentations/tcrm-ai
/Documentations/website
/Documentations/employees
/Documentations/recruitment
/Documentations/reports
/Documentations/administration
/Documentations/integrations
/Documentations/developer
/Documentations/security
/Documentations/release-notes
```

Nested pages must use lowercase slugs even though the root route retains the requested capitalized form.

Example:

```text
/Documentations/crm/lead-havuzu
/Documentations/crm/pipeline
/Documentations/crm/activities
```

### Redirect policy

- `/docs` → `/Documentations`
- `/documentation` → `/Documentations`
- `/documentations` → `/Documentations`
- old documentation URLs → the nearest equivalent page
- removed pages → a useful replacement page, not the home page
- unknown documentation slugs → a branded documentation 404

---

## 5. Global documentation layout

### Header

- TCRM logo
- Documentation label
- global search
- language selector
- version selector
- “Open TCRM” action
- mobile navigation button

### Left navigation

- collapsible section tree
- active page state
- module icons using TCRM-owned assets
- no third-party logos

### Main article

- breadcrumb
- title
- short purpose statement
- “Applies to” badges
- prerequisites
- numbered workflow
- screenshots
- notes, warnings, and examples
- related pages
- previous/next navigation
- last reviewed date

### Right-side table of contents

- headings from the current page
- sticky on desktop
- collapsible on mobile

### Footer

- TCRM copyright
- privacy
- terms
- security
- contact/support
- release notes
- documentation feedback

No upstream company name, logo, link, support button, forum link, product selector, pricing link, or hosted-platform reference may appear in the public design.

---

# 6. Complete TCRM documentation page plan

The list below is the required first public documentation release. Each bullet represents a separate page unless marked as a section landing page.

---

## 6.1 Documentation home

### `/Documentations`

Content:

- what the documentation covers;
- quick links for users, tenant administrators, software-owner administrators, and developers;
- featured guides;
- module cards;
- search;
- recently updated pages;
- current documentation version;
- support path;
- status of beta or experimental features.

### `/Documentations/whats-new`

Content:

- recently added documentation;
- changed workflows;
- renamed menus;
- deprecated features;
- links to release notes.

---

## 6.2 Getting started

### `/Documentations/getting-started`

Landing page for first-time users.

### `/Documentations/getting-started/what-is-tcrm`

- TCRM product overview;
- multi-tenant concept in plain language;
- supported business workflows;
- distinction between user, tenant administrator, and Software Owner.

### `/Documentations/getting-started/sign-in`

- tenant-specific login URL;
- password reset;
- invited-user activation;
- session behavior;
- safe troubleshooting.

### `/Documentations/getting-started/interface-tour`

- app launcher;
- top navigation;
- breadcrumbs;
- action menus;
- list, form, kanban, calendar, graph, and pivot views;
- chatter;
- mobile behavior.

### `/Documentations/getting-started/navigation`

- switching applications;
- browser back/forward behavior;
- opening linked records;
- favorites;
- recent items.

### `/Documentations/getting-started/search-filter-group`

- search;
- preconfigured filters;
- custom filters;
- group by;
- favorites;
- shared filters;
- access limitations.

### `/Documentations/getting-started/activities`

- scheduling activities;
- activity types;
- due dates;
- assignees;
- completion;
- next activity;
- link to Calendar and To-Do.

### `/Documentations/getting-started/notifications`

- in-app notifications;
- email notifications;
- mentions;
- followed records;
- user preferences.

### `/Documentations/getting-started/import-export`

- supported import formats;
- template download;
- field matching;
- validation;
- duplicate prevention;
- safe export rules;
- permissions.

### `/Documentations/getting-started/keyboard-shortcuts`

- command palette;
- navigation shortcuts;
- create/save/discard;
- accessibility notes.

### `/Documentations/getting-started/mobile`

- supported responsive workflows;
- limitations;
- mobile browser permissions;
- microphone permissions for Santral;
- file and camera uploads.

---

## 6.3 Core records and collaboration

### `/Documentations/core`

Landing page.

### `/Documentations/core/record-views`

- list;
- kanban;
- form;
- calendar;
- pivot;
- graph;
- activity view.

### `/Documentations/core/chatter`

- messages;
- internal notes;
- mentions;
- attachments;
- followers;
- activities;
- security implications.

### `/Documentations/core/tags-stages-teams`

- tags;
- stages;
- teams;
- ownership;
- company boundaries.

### `/Documentations/core/files-attachments`

- upload;
- preview;
- download;
- size limits;
- permitted file types;
- tenant isolation.

### `/Documentations/core/reporting-basics`

- measures;
- dimensions;
- filters;
- groupings;
- saved views;
- export permissions.

---

## 6.4 CRM

### `/Documentations/crm`

CRM overview and module landing page.

### `/Documentations/crm/lead-havuzu`

- the unified Lead Havuzu concept;
- leads and opportunities;
- list and kanban views;
- ownership;
- stage movement;
- qualification;
- access rules.

### `/Documentations/crm/create-lead`

- manual creation;
- required fields;
- source;
- project interest;
- contact;
- salesperson;
- tags;
- notes.

### `/Documentations/crm/import-leads`

- CSV/XLSX import;
- field mapping;
- phone normalization;
- email validation;
- duplicate detection;
- import logs.

### `/Documentations/crm/lead-sources`

- website forms;
- manual;
- referrals;
- Marketing Hub;
- campaigns;
- Santral;
- API;
- source attribution.

### `/Documentations/crm/assign-distribute`

- manual assignment;
- sales teams;
- distribution rules;
- reassignment;
- activity creation;
- user visibility.

### `/Documentations/crm/pipeline`

- stages;
- drag-and-drop;
- probability fields actually used by TCRM;
- expected revenue;
- next activity;
- won/lost;
- stage rules.

### `/Documentations/crm/lead-detail`

- contact details;
- project and unit interest;
- marketing source;
- call history;
- messages;
- activities;
- documents;
- quotations;
- payments where authorized.

### `/Documentations/crm/activities-calls-meetings`

- schedule activity;
- call through Santral;
- meeting;
- follow-up;
- reminders;
- calendar linkage.

### `/Documentations/crm/convert-merge`

- lead conversion;
- duplicate merge;
- preserving history;
- permissions;
- audit trail.

### `/Documentations/crm/won-lost`

- mark won;
- lost reason;
- restore;
- reporting effects.

### `/Documentations/crm/sales-teams`

- team setup;
- team leader;
- members;
- targets;
- assignment;
- visibility.

### `/Documentations/crm/marketing-attribution`

- campaign;
- ad set;
- ad;
- creative;
- page;
- form;
- UTM fields;
- source reporting.

### `/Documentations/crm/reports`

- lead volume;
- conversion;
- stage duration;
- unattended leads;
- lost reasons;
- salesperson performance;
- source performance;
- export and permissions.

### `/Documentations/crm/access-security`

- user roles;
- own/team/all records;
- company restrictions;
- AI access ceiling;
- tenant isolation.

---

## 6.5 Sales

### `/Documentations/sales`

Sales overview.

### `/Documentations/sales/products-services`

- products;
- services;
- categories;
- units;
- pricing fields;
- taxes only where supported.

### `/Documentations/sales/quotations`

- create quotation;
- customer;
- products;
- discounts;
- validity;
- notes;
- approval where implemented.

### `/Documentations/sales/send-quotation`

- email;
- portal/public link if implemented;
- PDF;
- activity tracking.

### `/Documentations/sales/confirm-order`

- quotation to order;
- state changes;
- linked CRM opportunity;
- delivery/invoicing effects actually supported.

### `/Documentations/sales/pricelists`

- supported pricing rules;
- currencies;
- customer-specific pricing;
- effective dates.

### `/Documentations/sales/invoicing-flow`

- invoice policy;
- create invoice;
- invoice state;
- payment linkage;
- exact boundaries of the TCRM implementation.

### `/Documentations/sales/commissions`

Publish only if the current TCRM module implements commissions.

### `/Documentations/sales/reports`

- quotation conversion;
- order totals;
- salesperson;
- product;
- time period;
- company and currency.

### `/Documentations/sales/permissions`

- sales user;
- manager;
- invoicing access;
- company and team restrictions.

---

## 6.6 Contacts

### `/Documentations/contacts`

Contacts overview.

### `/Documentations/contacts/create-contact`

- person versus company;
- phone;
- email;
- addresses;
- tags;
- language;
- salesperson.

### `/Documentations/contacts/companies-and-people`

- parent company;
- child contacts;
- invoicing and delivery addresses;
- linked CRM and sales records.

### `/Documentations/contacts/deduplication`

- duplicate identification;
- merge;
- safe review;
- activity and history preservation.

### `/Documentations/contacts/import-export`

- templates;
- unique identifiers;
- parent-company mapping;
- phone/email normalization.

### `/Documentations/contacts/privacy-access`

- visible fields;
- personal data;
- export control;
- deletion/archive;
- tenant isolation.

---

## 6.7 Propertio — Proje Stok ve Takibi

### `/Documentations/propertio`

Module overview.

### `/Documentations/propertio/project-types`

Document actual TCRM project types, including configured values such as:

- Konut;
- Villa;
- Ticari Dükkan;
- Karma;
- Devremülk;
- Arsa/Parsel;
- Kentsel Dönüşüm;
- other administrator-defined types.

### `/Documentations/propertio/project-stages`

Document actual stages, including configured values such as:

- Planlama;
- Ruhsat;
- Satışa Hazır;
- İnşaat;
- Teslime Hazır;
- Teslim Edildi;
- archived/cancelled states where implemented.

### `/Documentations/propertio/create-project`

- developer/owner;
- location;
- dates;
- stage;
- type;
- sales team;
- documents;
- media.

### `/Documentations/propertio/blocks-buildings-floors`

Publish only the structural levels implemented in the module.

### `/Documentations/propertio/units`

- unit number;
- type;
- area;
- floor;
- view;
- price;
- status;
- owner/customer;
- linked lead.

### `/Documentations/propertio/unit-statuses`

- available;
- reserved;
- optioned;
- sold;
- blocked;
- delivered;
- cancelled;
- exact transition rules.

### `/Documentations/propertio/reservations`

- reserve;
- expiry;
- assigned customer;
- payment;
- release;
- conflict prevention.

### `/Documentations/propertio/pricing`

- list price;
- campaign price;
- currency;
- payment plan;
- changes;
- audit fields.

### `/Documentations/propertio/link-to-crm`

- project interest;
- unit interest;
- matching lead;
- quotation;
- activities;
- call history.

### `/Documentations/propertio/documents-media`

- plans;
- images;
- contracts;
- authorization;
- file safety.

### `/Documentations/propertio/reports`

- available stock;
- reservations;
- sales;
- project progress;
- price ranges;
- salesperson;
- source attribution.

### `/Documentations/propertio/permissions`

- project manager;
- salesperson;
- finance;
- restricted data;
- multi-company and tenant rules.

---

## 6.8 Calendar and activities

### `/Documentations/calendar`

Calendar overview.

### `/Documentations/calendar/create-event`

- title;
- start/end;
- all-day;
- attendees;
- description;
- location;
- video link where supported.

### `/Documentations/calendar/recurring-events`

- recurrence;
- end date;
- timezone;
- edit one versus series.

### `/Documentations/calendar/reminders`

- in-app;
- email;
- configured reminders;
- overdue activities.

### `/Documentations/calendar/team-availability`

Publish only if available in the current TCRM build.

### `/Documentations/calendar/crm-project-integration`

- meetings from a lead;
- activities from a task;
- linked record navigation.

### `/Documentations/calendar/external-sync`

Document Google/Outlook synchronization only if TCRM has a tested and supported configuration.

---

## 6.9 To-Do

### `/Documentations/todo`

Overview.

### `/Documentations/todo/create-manage`

- create;
- title;
- description;
- tags;
- assignees;
- stages;
- drag-and-drop.

### `/Documentations/todo/activities-reminders`

- schedule;
- due dates;
- responsible user;
- complete/reschedule.

### `/Documentations/todo/convert-to-task`

- convert to project task;
- project;
- assignee;
- tags;
- resulting visibility.

### `/Documentations/todo/private-shared`

- private work;
- sharing;
- permissions.

---

## 6.10 Messaging

### `/Documentations/messaging`

Overview.

### `/Documentations/messaging/inbox`

- unread;
- mentions;
- history;
- starred items.

### `/Documentations/messaging/direct-messages`

- one-to-one;
- group chat;
- reactions;
- replies;
- attachments;
- message actions.

### `/Documentations/messaging/channels`

- create;
- members;
- public/private;
- moderation;
- notifications.

### `/Documentations/messaging/chatter`

- record discussions;
- internal notes;
- mentions;
- followers;
- linked activity.

### `/Documentations/messaging/notifications`

- browser;
- in-app;
- email;
- user preferences.

### `/Documentations/messaging/calls`

Document only the actual TCRM meeting/call capability. Do not mix internal video chat with Santral PSTN calling.

### `/Documentations/messaging/security`

- private conversations;
- channel membership;
- attachments;
- tenant isolation.

---

## 6.11 Projects

### `/Documentations/projects`

Overview.

### `/Documentations/projects/create-project`

- name;
- manager;
- members;
- privacy;
- company;
- stages.

### `/Documentations/projects/tasks`

- create task;
- assignees;
- deadline;
- tags;
- description;
- sub-tasks if implemented;
- dependencies if implemented.

### `/Documentations/projects/stages-kanban`

- stages;
- drag-and-drop;
- folded stages;
- status.

### `/Documentations/projects/activities-chatter`

- reminders;
- messages;
- documents;
- linked records.

### `/Documentations/projects/milestones`

Publish only if implemented.

### `/Documentations/projects/reporting`

- task status;
- overdue;
- assignee;
- project progress;
- time or profitability only if implemented.

### `/Documentations/projects/permissions`

- private;
- invited users;
- company access;
- external/portal behavior if supported.

---

## 6.12 Invoicing and payments

### `/Documentations/invoicing`

Overview and clear feature boundaries.

### `/Documentations/invoicing/customer-invoices`

- create;
- customer;
- invoice lines;
- currency;
- due date;
- posting/confirmation;
- PDF.

### `/Documentations/invoicing/credit-notes`

Publish only if supported and tested.

### `/Documentations/invoicing/payments`

- register payment;
- payment method;
- date;
- amount;
- reconciliation behavior actually implemented;
- audit trail.

### `/Documentations/invoicing/installments`

- payment plan;
- schedule;
- due dates;
- paid/unpaid;
- overdue;
- linked property/unit.

### `/Documentations/invoicing/overdue-collections`

- overdue list;
- follow-up;
- activities;
- reports;
- permissions.

### `/Documentations/invoicing/reports`

- invoiced;
- collected;
- outstanding;
- overdue;
- period;
- company;
- currency;
- deterministic totals.

### `/Documentations/invoicing/security`

- finance roles;
- deletion restrictions;
- payment immutability;
- AI access restrictions;
- audit records.

---

## 6.13 Marketing Hub

### `/Documentations/marketing-hub`

Overview.

### `/Documentations/marketing-hub/api-profiles`

- create profile;
- provider;
- account;
- secure credentials;
- test connection;
- permissions.

### `/Documentations/marketing-hub/pages-accounts`

- select pages;
- ad accounts;
- scope;
- synchronization.

### `/Documentations/marketing-hub/campaigns`

- campaigns;
- ad sets;
- ads;
- status;
- date ranges;
- spend metrics available from the provider.

### `/Documentations/marketing-hub/creatives`

- creative preview;
- media;
- copy;
- destination;
- deduplication;
- source identifiers.

### `/Documentations/marketing-hub/lead-forms`

- forms;
- questions;
- synchronization;
- mapping to Lead Havuzu;
- duplicate prevention.

### `/Documentations/marketing-hub/attribution`

- campaign to lead;
- first/last source where implemented;
- page/form/ad/creative identifiers.

### `/Documentations/marketing-hub/reports`

- leads;
- cost fields if available;
- conversion;
- source;
- salesperson;
- project;
- date range.

### `/Documentations/marketing-hub/security`

- encrypted credentials;
- tenant-local settings;
- access groups;
- no owner-secret propagation.

---

## 6.14 Santral

### `/Documentations/santral`

Overview and supported countries/providers.

### `/Documentations/santral/configuration`

- provider;
- account identifier;
- application identifier;
- caller ID;
- webhooks;
- test connection;
- secure secret storage.

### `/Documentations/santral/browser-permissions`

- microphone;
- speaker;
- browser compatibility;
- network requirements;
- troubleshooting.

### `/Documentations/santral/call-from-lead`

- click phone number;
- call panel;
- active call;
- customer context;
- notes.

### `/Documentations/santral/call-controls`

- answer;
- hang up;
- mute;
- unmute;
- device selection;
- clearly state whether hold/transfer is supported.

### `/Documentations/santral/call-statuses`

- initiated;
- ringing;
- answered;
- completed;
- busy;
- no answer;
- declined;
- failed;
- provider blocked.

### `/Documentations/santral/recordings`

- recording state;
- playback;
- access control;
- retention;
- consent notice requirements;
- download only where authorized.

### `/Documentations/santral/call-logs`

- parent and child call records;
- destination;
- duration;
- outcome;
- recording;
- linked lead/contact;
- administrator diagnostics.

### `/Documentations/santral/troubleshooting`

- invalid caller ID;
- geo permission;
- declined;
- no answer;
- provider blacklist;
- audio cutting;
- firewall/network;
- safe information to send to support.

### `/Documentations/santral/security-privacy`

- tenant-local credentials;
- webhook signature validation;
- recording access;
- retention;
- audit trail.

---

## 6.15 TCRM AI

### `/Documentations/tcrm-ai`

Overview.

### `/Documentations/tcrm-ai/access-entitlement`

- Software Owner entitlement;
- tenant activation;
- user groups;
- revoked/suspended states.

### `/Documentations/tcrm-ai/provider-configuration`

- choose approved provider;
- choose approved model;
- enter key;
- save;
- test connection;
- mask/change/delete key.

### `/Documentations/tcrm-ai/chat`

- full-page chat;
- floating assistant;
- conversations;
- streaming;
- stop/retry;
- sources.

### `/Documentations/tcrm-ai/ask-business-questions`

- CRM;
- sales;
- inventory;
- projects;
- payments;
- reports;
- example prompts;
- current-user access boundary.

### `/Documentations/tcrm-ai/reports`

- deterministic data tools;
- report period;
- filters;
- company;
- currency;
- evidence;
- export permissions.

### `/Documentations/tcrm-ai/internet-research`

- real-time public data;
- sources;
- retrieval time;
- tenant setting;
- limitations;
- separation from TCRM business data.

### `/Documentations/tcrm-ai/privacy-security`

- no direct database credentials;
- read-only approved tools;
- current-user ACLs and record rules;
- tenant isolation;
- provider data controls;
- secret handling.

### `/Documentations/tcrm-ai/usage-quotas`

- request limits;
- token limits;
- rate limiting;
- retry messages;
- administrator dashboard.

### `/Documentations/tcrm-ai/troubleshooting`

- key invalid;
- model not allowed;
- quota exceeded;
- timeout;
- provider unavailable;
- entitlement missing;
- configuration incomplete.

---

## 6.16 Website

### `/Documentations/website`

Overview.

### `/Documentations/website/pages`

- create/edit;
- menus;
- publish/unpublish;
- access.

### `/Documentations/website/content-blocks`

Document only blocks available in TCRM.

### `/Documentations/website/forms`

- contact/lead forms;
- field mapping;
- consent;
- spam protection;
- CRM source.

### `/Documentations/website/domains`

- tenant domain;
- custom domain;
- DNS requirements;
- certificate status;
- routing;
- unknown domain behavior.

### `/Documentations/website/seo`

- page title;
- description;
- canonical;
- sitemap;
- robots;
- redirects.

### `/Documentations/website/media`

- upload;
- optimization;
- alt text;
- supported types;
- no third-party copyrighted assets.

---

## 6.17 Employees

### `/Documentations/employees`

Overview.

### `/Documentations/employees/create-manage`

- employee;
- work contact;
- department;
- manager;
- job position;
- company.

### `/Documentations/employees/departments`

- hierarchy;
- manager;
- members.

### `/Documentations/employees/access-privacy`

- HR access;
- public/private fields;
- company boundaries;
- archive.

Publish attendance, leave, fleet, payroll, lunch, appraisal, or referral documentation only when the matching TCRM feature is installed and independently verified.

---

## 6.18 Recruitment

### `/Documentations/recruitment`

Overview.

### `/Documentations/recruitment/job-positions`

- create position;
- department;
- recruiter;
- stage;
- website publishing if supported.

### `/Documentations/recruitment/applicants`

- create/import;
- CV;
- contact;
- source;
- assigned recruiter.

### `/Documentations/recruitment/pipeline`

- stages;
- activities;
- interviews;
- hired/refused;
- reasons.

### `/Documentations/recruitment/permissions`

- HR role;
- recruiter;
- private documents;
- tenant isolation.

---

## 6.19 Reports and dashboards

### `/Documentations/reports`

Overview.

### `/Documentations/reports/search-filters`

- periods;
- companies;
- teams;
- users;
- projects;
- sources.

### `/Documentations/reports/pivot-graph`

- measures;
- grouping;
- chart types;
- drill-down;
- restrictions.

### `/Documentations/reports/save-share`

- saved filters;
- private/shared;
- default view;
- permissions.

### `/Documentations/reports/export`

- PDF;
- CSV/XLSX;
- authorized data only;
- formatting;
- currency and timezone.

### `/Documentations/reports/tcrm-panels`

- dashboard selection;
- cards;
- refresh;
- filters;
- drill-through.

### `/Documentations/reports/ai-generated`

- verified tool results;
- evidence;
- date range;
- user;
- company;
- saved report;
- no arbitrary SQL.

---

## 6.20 Tenant administration

### `/Documentations/administration`

Landing page.

### `/Documentations/administration/users`

- invite;
- activate;
- deactivate;
- reset;
- groups;
- company access.

### `/Documentations/administration/roles-permissions`

- least privilege;
- business roles;
- module groups;
- record rules;
- testing access.

### `/Documentations/administration/companies`

- company configuration;
- allowed companies;
- switching;
- cross-company restrictions.

### `/Documentations/administration/modules`

- module entitlement;
- installed state;
- access state;
- configuration state;
- dependency handling.

### `/Documentations/administration/tenant-profile`

- tenant name;
- domain;
- language;
- timezone;
- company;
- status.

### `/Documentations/administration/domains-tls`

- wildcard domain;
- custom domain;
- mapping;
- DNS;
- TLS;
- certificate verification;
- no database selector.

### `/Documentations/administration/usage-limits`

- plan;
- module limits;
- AI usage;
- call usage;
- storage;
- safe messages.

### `/Documentations/administration/audit-logs`

- user actions;
- AI tool calls;
- calls;
- integrations;
- safe filters;
- retention.

### `/Documentations/administration/backup-restore`

Publish only supported tenant administrator capabilities. Keep infrastructure-only recovery procedures in restricted internal documentation.

---

## 6.21 TCRM Master — Software Owner

These pages may be public at a high level, but operational secrets and exact infrastructure commands must be in restricted internal documentation.

### `/Documentations/tcrm-master`

Overview.

### `/Documentations/tcrm-master/tenant-lifecycle`

- draft;
- pending;
- provisioning;
- active;
- suspended;
- failed;
- decommissioning;
- archived.

### `/Documentations/tcrm-master/provisioning`

- what provisioning performs;
- safe job states;
- retry;
- activation gate;
- no public database manager.

### `/Documentations/tcrm-master/application-catalog`

- catalog;
- entitlement;
- actual installed state;
- sync;
- stale state;
- dependencies.

### `/Documentations/tcrm-master/grant-revoke-access`

- grant;
- revoke;
- preserve data;
- separate uninstallation;
- audit.

### `/Documentations/tcrm-master/domains-routing`

- explicit domain mapping;
- wildcard domains;
- custom domains;
- unknown-domain 404;
- tenant isolation.

### `/Documentations/tcrm-master/tenant-360`

- overview;
- users;
- modules;
- finance;
- domains;
- safe status.

### `/Documentations/tcrm-master/security`

- no tenant business-data browsing by default;
- no plaintext tenant secrets;
- audited administrative operations;
- database-per-tenant boundaries.

---

## 6.22 Integrations

### `/Documentations/integrations`

Landing page.

### `/Documentations/integrations/email`

- outgoing/incoming email;
- aliases;
- safe configuration;
- troubleshooting.

### `/Documentations/integrations/calendar`

- Google;
- Outlook;
- scopes;
- tenant-local credentials;
- revoke.

### `/Documentations/integrations/meta`

- API profile;
- pages;
- ad accounts;
- lead forms;
- sync;
- permissions.

### `/Documentations/integrations/twilio`

- application;
- number;
- callbacks;
- geo permissions;
- troubleshooting;
- tenant-local configuration.

### `/Documentations/integrations/groq`

- project;
- allowed model;
- key;
- zero-data-retention setting;
- rate limits;
- tenant-local configuration.

### `/Documentations/integrations/webhooks`

- supported events;
- signing;
- replay protection;
- retries;
- logs.

### `/Documentations/integrations/api`

- supported TCRM external API;
- authentication;
- scopes;
- pagination;
- rate limits;
- examples written for TCRM;
- no raw database access.

---

## 6.23 Security and privacy

### `/Documentations/security`

Landing page.

### `/Documentations/security/tenant-isolation`

- database-per-tenant;
- domain mapping;
- sessions;
- files;
- AI;
- integrations.

### `/Documentations/security/access-control`

- ACLs;
- record rules;
- companies;
- groups;
- least privilege.

### `/Documentations/security/secrets`

- encryption;
- masking;
- frontend prohibition;
- logs;
- rotation.

### `/Documentations/security/ai`

- tool access;
- no SQL;
- user-equivalent permissions;
- internet separation;
- audit.

### `/Documentations/security/call-recordings`

- authorization;
- consent;
- retention;
- access logs.

### `/Documentations/security/report-issue`

- responsible disclosure contact;
- required details;
- no public secret posting.

---

## 6.24 Developer documentation

The public developer documentation must be TCRM-specific. Do not copy the complete upstream framework reference.

### `/Documentations/developer`

Landing page.

### `/Documentations/developer/environment`

- supported Python/PostgreSQL/runtime;
- repository structure;
- development database;
- secrets;
- local setup.

### `/Documentations/developer/addon-structure`

- manifest;
- models;
- views;
- security;
- data;
- tests;
- assets.

### `/Documentations/developer/models-orm`

- TCRM conventions;
- safe ORM usage;
- tenant context;
- no raw tenant switching;
- computed fields;
- constraints.

### `/Documentations/developer/security`

- ACL;
- record rules;
- company rules;
- avoiding `sudo()`;
- controllers;
- CSRF;
- secret models.

### `/Documentations/developer/views-actions-menus`

- XML;
- actions;
- menus;
- inherited views;
- naming conventions.

### `/Documentations/developer/owl-frontend`

- component structure;
- services;
- registries;
- assets;
- tests;
- global floating widgets.

### `/Documentations/developer/controllers-api`

- public versus authenticated routes;
- JSON responses;
- status codes;
- rate limits;
- signature validation.

### `/Documentations/developer/multi-tenant-routing`

- explicit mapping;
- master database;
- tenant database;
- unknown domain;
- sessions;
- tests.

### `/Documentations/developer/provisioning`

- background job;
- fixed command allowlist;
- idempotency;
- activation gate;
- failure handling.

### `/Documentations/developer/testing`

- unit;
- integration;
- frontend;
- tenant-isolation;
- real acceptance testing;
- disposable tenant.

### `/Documentations/developer/deployment`

- module upgrade;
- database backup;
- assets;
- restart;
- health checks;
- rollback.

### `/Documentations/developer/migrations`

- schema changes;
- upgrade scripts;
- per-tenant execution;
- idempotency;
- verification.

### `/Documentations/developer/contributing`

- branch;
- commit;
- review;
- tests;
- no secrets;
- source-of-truth rules.

---

## 6.25 Release notes and lifecycle

### `/Documentations/release-notes`

- releases by date/version;
- new;
- changed;
- fixed;
- security;
- migration required;
- module upgrade required.

### `/Documentations/supported-versions`

- supported TCRM versions;
- maintenance status;
- end-of-support dates;
- upgrade path.

### `/Documentations/deprecations`

- deprecated routes;
- models;
- settings;
- replacement;
- removal date.

---

# 7. Standard article template

Every page must use this front matter or equivalent database fields:

```yaml
title: "Lead Havuzu"
slug: "crm/lead-havuzu"
summary: "Lead ve fırsat kayıtlarını tek havuzda yönetin."
audience:
  - sales-user
  - sales-manager
applies_to:
  - tcrm_crm
minimum_version: "19.0-tcrm.1"
status: "published"
language: "tr"
last_reviewed: "YYYY-MM-DD"
owner: "CRM Product Team"
keywords:
  - lead
  - fırsat
  - crm
```

Every article body should follow this sequence:

1. Purpose
2. Before you start
3. Access required
4. Main workflow
5. Field reference when needed
6. Example
7. What happens next
8. Troubleshooting
9. Security and permissions
10. Related pages
11. Last reviewed

---

# 8. Content authoring rules

## Required

- Write original TCRM text.
- Verify labels against the current Turkish and English UI.
- Use the exact current menu path.
- Use staging screenshots with demo data.
- Blur personal data and secrets.
- State required roles.
- State edition/plan/module requirements.
- State limitations honestly.
- Use short procedures with one action per step.
- Add alt text to every image.
- Add code blocks only when necessary.
- Test every link.
- Review after any menu, field, or workflow change.

## Prohibited

- copying paragraphs from upstream docs;
- translating copied paragraphs without attribution;
- replacing an upstream brand name mechanically;
- copying upstream images or diagrams;
- using upstream logos;
- embedding upstream pages;
- proxying upstream HTML;
- hotlinking assets;
- publishing enterprise-only instructions for missing TCRM features;
- claiming unsupported features;
- exposing customer, tenant, database, key, webhook, or server details.

---

# 9. Content storage architecture

Recommended implementation: a dedicated custom addon named `tcrm_documentation`.

```text
custom_addons/tcrm_documentation/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   ├── documentation.py
│   └── search.py
├── models/
│   ├── __init__.py
│   ├── documentation_page.py
│   ├── documentation_category.py
│   ├── documentation_redirect.py
│   └── documentation_feedback.py
├── security/
│   ├── ir.model.access.csv
│   └── documentation_security.xml
├── views/
│   ├── documentation_backend_views.xml
│   ├── documentation_menus.xml
│   └── website_templates.xml
├── data/
│   ├── categories.xml
│   ├── redirects.xml
│   └── pages/
│       ├── tr/
│       └── en/
├── static/
│   ├── src/
│   │   ├── scss/documentation.scss
│   │   ├── js/documentation_search.js
│   │   └── js/documentation_nav.js
│   └── img/
├── tests/
│   ├── test_routes.py
│   ├── test_search.py
│   ├── test_permissions.py
│   ├── test_redirects.py
│   └── test_content_quality.py
└── README.md
```

### Storage recommendation

Keep canonical article source in Git-tracked Markdown or sanitized HTML files. Import/update pages idempotently during module upgrade.

Do not make production database edits the only source of truth.

### Suggested models

#### `tcrm.documentation.category`

- name
- slug
- parent_id
- sequence
- icon
- published
- audience
- module_dependencies

#### `tcrm.documentation.page`

- title
- slug
- summary
- body
- language
- category_id
- parent_page_id
- sequence
- status
- minimum_version
- last_reviewed
- owner
- keywords
- module_dependencies
- public
- search_text
- checksum

#### `tcrm.documentation.redirect`

- old_path
- target_page_id or target_path
- HTTP status
- active

#### `tcrm.documentation.feedback`

- page
- helpful
- message
- optional authenticated user
- creation date
- status

---

# 10. Search requirements

- full-text search over title, summary, headings, keywords, and body;
- Turkish-aware normalization;
- typo tolerance;
- weighted title matches;
- category filter;
- audience filter;
- language filter;
- keyboard navigation;
- highlighted snippets;
- empty-state suggestions;
- no external search dependency required for the first version;
- no indexing of drafts, secrets, or internal-only pages.

The search endpoint must rate-limit anonymous requests.

---

# 11. Multilingual requirements

Initial languages:

- Turkish as default;
- English as secondary.

Rules:

- independent translated pages;
- stable language-neutral page identifier;
- hreflang metadata;
- preserve slug redirects;
- show fallback only when explicitly allowed;
- never display mixed-language navigation.

---

# 12. SEO and accessibility

- unique title and description;
- canonical URL;
- XML sitemap;
- breadcrumbs structured data;
- article structured data where suitable;
- OpenGraph metadata;
- meaningful heading hierarchy;
- keyboard navigation;
- visible focus;
- sufficient contrast;
- alt text;
- responsive tables;
- skip-to-content link;
- no layout shift from navigation;
- fast first contentful render.

---

# 13. Removal and migration of the current public documentation

Do not delete the existing pages blindly.

1. Inventory all current documentation routes.
2. Export titles, slugs, language, status, and inbound links.
3. Take a database and file backup.
4. Create a route-by-route migration map.
5. Build the new module in staging.
6. Create permanent redirects for valid old pages.
7. Return 410 only for content intentionally removed with no replacement.
8. Verify search-engine sitemap and canonical URLs.
9. Remove or unpublish old pages only after the new pages pass acceptance tests.
10. Keep rollback instructions.

---

# 14. Acceptance criteria

The first release is complete only when:

- `/Documentations` loads anonymously over HTTPS;
- all aliases redirect correctly;
- no public page contains upstream brand names, logos, links, assets, or copied text;
- all published pages correspond to real TCRM features;
- premium-only upstream topics are excluded unless independently implemented by TCRM;
- Turkish and English navigation work;
- search works;
- mobile navigation works;
- breadcrumbs and on-page table of contents work;
- old documentation routes have reviewed redirects;
- sitemap contains published documentation pages;
- drafts are not public;
- Markdown/HTML is sanitized;
- no secret or customer data is present;
- tests pass;
- screenshots are TCRM-owned staging captures;
- every page has an owner and last-reviewed date.

---

# 15. Cursor Agent implementation prompt

Copy the prompt below into Cursor Agent.

```text
Build a production-quality public TCRM documentation website at:

https://tcrm.online/Documentations

Do not enter Plan Mode.
Do not create a disposable prototype.
Audit the existing TCRM public website, documentation routes, custom addons, theme, routing, localization, and deployment structure before editing.

The attached specification file is the source of truth for the documentation information architecture and required pages.

==================================================
A. COPYRIGHT AND CONTENT SAFETY
==================================================

The official upstream 19.0 documentation may be used only as a research checklist.

Do not:

- copy paragraphs;
- translate copied paragraphs;
- mechanically replace the upstream product name with TCRM;
- copy screenshots, diagrams, icons, logos, CSS, HTML, templates, or source documentation files;
- embed, proxy, scrape, or hotlink upstream documentation pages;
- strip attribution from adapted CC BY-SA material;
- publish premium/proprietary feature documentation unless the same feature exists independently in TCRM.

Create original TCRM documentation from:

1. the current TCRM source code;
2. actual models, fields, menus, actions, views, access groups, and workflows;
3. a staging tenant with demo data;
4. existing internal TCRM specifications;
5. verified acceptance tests.

The public documentation must contain only TCRM branding and TCRM-owned screenshots.

If any existing TCRM documentation contains copied or adapted third-party content, quarantine it for review rather than silently republishing it.

==================================================
B. MAIN OBJECTIVE
==================================================

Create or complete a dedicated addon:

tcrm_documentation

It must provide:

- public documentation home;
- hierarchical navigation;
- article pages;
- Turkish and English content;
- full-text search;
- breadcrumbs;
- on-page table of contents;
- previous/next navigation;
- version metadata;
- module requirement badges;
- responsive mobile design;
- SEO metadata;
- sitemap;
- redirect management;
- feedback;
- backend content administration;
- Git-tracked canonical content;
- automated tests.

Canonical route:

/Documentations

Create permanent aliases:

/docs
/documentation
/documentations

All aliases must redirect to /Documentations.

Nested slugs must be lowercase:

/Documentations/crm/lead-havuzu

==================================================
C. AUDIT FIRST
==================================================

Before implementation, report:

- existing documentation addons;
- existing website pages;
- existing routes under /docs, /documentation, /documentations, and similar paths;
- current public theme/layout;
- current language configuration;
- current sitemap implementation;
- current search implementation;
- all current documentation content locations;
- any copied third-party branding or text;
- inbound route references found in templates, menus, source, and redirects;
- modules currently installed in production and staging;
- which requested documentation sections have real TCRM implementations.

Do not claim support for a page merely because an upstream documentation page exists.

==================================================
D. PAGE SCOPE
==================================================

Implement the complete page tree in this specification.

Prioritize the first release in this order:

1. Documentation home
2. Getting Started
3. Core interface
4. CRM
5. Sales
6. Contacts
7. Propertio
8. Calendar
9. To-Do
10. Messaging
11. Projects
12. Invoicing and payments
13. Marketing Hub
14. Santral
15. TCRM AI
16. Reports
17. Tenant administration
18. TCRM Master
19. Integrations
20. Security
21. Website
22. Employees
23. Recruitment
24. Developer documentation
25. Release notes

Every requested page must be classified as:

- implemented and documented;
- implemented but documentation pending;
- not implemented;
- internal-only;
- excluded because it is upstream premium/proprietary;
- excluded because it is irrelevant to TCRM.

Do not publish placeholder pages as completed documentation.

==================================================
E. CONTENT GENERATION
==================================================

For every page:

1. Inspect the actual module manifest.
2. Inspect the actual menus and actions.
3. Inspect the actual views and field labels.
4. Inspect security groups and record rules.
5. Inspect backend behavior.
6. Reproduce the workflow in a staging tenant.
7. Write original Turkish content.
8. Write an original English translation.
9. Capture new TCRM screenshots.
10. Add prerequisites, permissions, steps, troubleshooting, and related pages.
11. Record module dependency and minimum TCRM version.
12. Add owner and last-reviewed date.

Do not invent features or labels.

Where a requested feature is absent, do not fabricate documentation. Mark it as not implemented in the internal completion report.

==================================================
F. TECHNICAL ARCHITECTURE
==================================================

Use a dedicated addon structure consistent with the repository.

Canonical article content must be Git-tracked.

Preferred approach:

- Markdown or sanitized HTML source files in the addon;
- idempotent importer during module installation/upgrade;
- database records for rendering, search indexing, state, translations, and feedback;
- stable external IDs;
- checksums to avoid destructive overwrites;
- editorial override policy documented.

Create models equivalent to:

- tcrm.documentation.category
- tcrm.documentation.page
- tcrm.documentation.redirect
- tcrm.documentation.feedback

Adapt names to repository conventions if equivalent models already exist.

Do not create duplicate models if a safe existing documentation subsystem can be extended.

==================================================
G. SECURITY
==================================================

Public readers may access only published public pages.

Backend editing must require an explicit documentation administrator group.

Sanitize all article HTML.

Block:

- script tags;
- inline event handlers;
- unsafe iframes;
- javascript URLs;
- untrusted embeds;
- arbitrary template expressions.

Do not expose:

- API keys;
- database names;
- internal hosts;
- private IP addresses;
- tenant identifiers not intended for publication;
- customer data;
- webhook secrets;
- server paths;
- stack traces;
- internal operational commands on public pages.

Internal Software Owner runbooks must remain private and separate from public docs.

Rate-limit anonymous search and feedback endpoints.

Apply CSRF protection where appropriate.

==================================================
H. PUBLIC UI
==================================================

Build a TCRM-owned documentation design.

Header:

- TCRM logo;
- Documentation title;
- search;
- language;
- version;
- Open TCRM button.

Desktop:

- left hierarchical navigation;
- centered article;
- right on-page table of contents.

Mobile:

- slide-out navigation;
- search;
- collapsible page table of contents;
- readable code blocks and tables.

Remove all third-party branding, links, logos, product selectors, support buttons, and footer references from the public layout.

Do not imitate the upstream website pixel-for-pixel.

Use the existing TCRM public design system and brand tokens.

==================================================
I. SEARCH
==================================================

Implement server-side search over published pages.

Index:

- title;
- summary;
- headings;
- keywords;
- body;
- category.

Requirements:

- Turkish character normalization;
- title weighting;
- typo-tolerant behavior where practical;
- highlighted result snippets;
- category and language filters;
- keyboard navigation;
- no draft/internal results;
- anonymous rate limiting;
- safe query length.

Add tests for Turkish searches such as:

- lead havuzu
- fırsat
- gecikmiş ödeme
- santral
- proje stok
- yapay zekâ

==================================================
J. SEO, SITEMAP, AND REDIRECTS
==================================================

Add:

- unique page title;
- meta description;
- canonical URL;
- hreflang;
- breadcrumbs;
- XML sitemap;
- robots behavior;
- OpenGraph;
- structured data where appropriate.

Audit all existing documentation URLs and create a reviewed redirect map.

Do not redirect every removed page to the documentation home.

Use:

- 301 for permanent replacements;
- 404 for unknown slugs;
- 410 only when intentionally removed without replacement.

==================================================
K. CURRENT DOCUMENTATION MIGRATION
==================================================

Do not remove current production documentation before:

1. backup;
2. inventory;
3. content review;
4. redirect mapping;
5. staging deployment;
6. acceptance tests.

Classify existing content:

- retain and rewrite;
- merge;
- redirect;
- archive;
- remove.

Do not republish copied third-party text.

After acceptance, unpublish or remove the old documentation implementation and verify there are no duplicate canonical pages.

==================================================
L. SCREENSHOTS
==================================================

Use only screenshots captured from a disposable TCRM staging tenant.

Requirements:

- demo data only;
- no real customer names;
- no API keys;
- no phone numbers belonging to real people;
- no email addresses belonging to real people;
- no internal server information;
- consistent browser size;
- Turkish screenshot set;
- English screenshot set where labels differ;
- descriptive filenames;
- alt text;
- optimized WebP/PNG;
- no upstream images or logos.

==================================================
M. TESTS
==================================================

Add automated tests for:

Routes:

- /Documentations returns 200;
- aliases return permanent redirects;
- nested pages return 200;
- unknown page returns branded 404;
- draft page is not public;
- internal page is not public.

Security:

- public cannot edit;
- documentation admin can edit;
- unsafe HTML is sanitized;
- search excludes drafts;
- feedback endpoint is protected and rate-limited;
- no secret patterns in published content.

Content:

- every published page has title, slug, summary, language, owner, and last-reviewed date;
- slugs are unique;
- internal links resolve;
- images have alt text;
- no banned third-party branding in rendered public content;
- no prohibited external asset URLs;
- required module metadata exists.

Search:

- Turkish and English searches;
- typo behavior;
- filters;
- no draft leakage.

SEO:

- canonical;
- hreflang;
- sitemap;
- breadcrumbs;
- metadata.

Responsive frontend:

- desktop navigation;
- mobile drawer;
- table of contents;
- code blocks;
- tables;
- keyboard navigation.

Migration:

- old routes redirect correctly;
- no redirect loops;
- no duplicate canonical pages.

==================================================
N. REAL ACCEPTANCE TEST
==================================================

Deploy to staging and verify:

1. Anonymous visitor opens /Documentations.
2. Search works in Turkish.
3. Mobile navigation works.
4. CRM Lead Havuzu guide matches the real UI.
5. Propertio guide matches actual project/unit fields.
6. Santral guide matches current call controls and statuses.
7. TCRM AI guide matches actual entitlement, settings, chat, and privacy behavior.
8. A tenant administrator guide does not expose Software Owner secrets.
9. No page contains third-party logos, links, copied screenshots, or copied text.
10. No premium-only feature is presented as available unless implemented by TCRM.
11. Old documentation URLs resolve through reviewed redirects.
12. Sitemap and canonical tags are correct.
13. All public pages render over HTTPS.
14. There are no mixed-language navigation elements.
15. Performance is acceptable on mobile.

==================================================
O. DEPLOYMENT
==================================================

Before production:

- back up the affected database;
- back up current documentation content;
- record current routes;
- run module tests;
- upgrade the documentation addon explicitly;
- rebuild assets;
- restart services safely;
- clear stale assets;
- verify redirects;
- verify sitemap;
- verify public anonymous access;
- verify backend editor permissions;
- keep rollback instructions.

Do not commit secrets, screenshots containing secrets, dumps, tarballs, logs, or scratch scripts.

Do not commit unless explicitly instructed.

==================================================
P. FINAL REPORT
==================================================

Provide:

- audit findings;
- current documentation inventory;
- copyright-risk findings;
- implemented page tree;
- excluded page tree and reasons;
- modified files;
- new files;
- models;
- routes;
- templates;
- assets;
- translations;
- redirect map;
- search design;
- sanitization design;
- tests and results;
- staging acceptance results;
- screenshots;
- exact module upgrade commands;
- exact deployment commands;
- rollback steps;
- remaining undocumented implemented features;
- Git diff summary.

Do not claim “full documentation complete” until every published page is verified against the current TCRM interface and all acceptance tests pass.
```

---

# 16. Research sources

Primary research sources used for the hierarchy and scope review:

- Official 19.0 documentation home and user-documentation hierarchy.
- Official documentation source repository, branch 19.0.
- Official source-repository license: CC BY-SA 4.0.
- Official community software licensing and administration overview.
- Official category index files for Essentials, Finance, Sales, Websites, Supply Chain, Human Resources, Marketing, Services, Productivity, General Settings, Administration, and Developer documentation.
- Official CRM, Sales, Project, Calendar, Discuss, and To-Do page structures.

This file intentionally does not include copied full-text documentation or copied screenshots.
