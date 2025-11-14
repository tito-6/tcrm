# Safe Webhook Integration Plan for Odoo CRM

## Analysis Summary

### Current Odoo State
- Fresh Odoo 17.0 installation
- Database: `crm`
- Clean installation with base modules only
- UI fully functional at http://localhost:8069

### Webhook System Components
Your webhook system consists of:

1. **webhooks_bridge** - Odoo addon that exposes HTTP endpoints
   - `/webhooks/meta` - Receives Meta/Facebook Lead Ads webhooks
   - `/webhooks/google` - Receives Google Ads webhooks
   - Depends on: `base`, `crm`
   
2. **meta_leads** - Odoo addon for Meta lead management
   - Adds custom fields to CRM leads (meta_leadgen_id, meta_page_id, etc.)
   - Mapping rules for auto-assignment to sales teams/users
   - Depends on: `crm`

3. **External Scripts**
   - `fetch_meta_leads.py` - Manual lead fetching from Meta API
   - `initialize_clients.py` - API client initialization

## Safety Analysis

### ✅ Safe Aspects
1. **Modular Design**: Addons are self-contained and use proper Odoo module structure
2. **Non-Intrusive**: Only extends existing CRM model, doesn't modify core
3. **Proper Dependencies**: Clearly declares dependencies on `base` and `crm`
4. **Public Endpoints**: Uses `auth='public'` and `csrf=False` correctly for webhooks
5. **Error Handling**: Has try-except blocks to prevent crashes

### ⚠️ Potential Risks & Mitigations

1. **Module Version Mismatch**
   - **Risk**: Manifests show version 18.0, but Odoo is 17.0
   - **Fix**: Update manifest versions to 17.0
   
2. **Database Schema Changes**
   - **Risk**: Adding custom fields to crm.lead could cause issues
   - **Mitigation**: Always backup before installing
   
3. **External Dependencies**
   - **Risk**: Webhook code uses `requests` library
   - **Mitigation**: Verify it's installed in Odoo container

4. **Environment Variables**
   - **Risk**: Webhook expects META_APP_ID, META_APP_SECRET in container env
   - **Mitigation**: Add to docker-compose.yml properly

## Safe Integration Steps

### Phase 1: Preparation (No Odoo Changes)
1. ✅ Copy addons to safe location
2. ✅ Update manifest versions from 18.0 to 17.0
3. ✅ Verify credentials in .env file
4. ✅ Test external scripts independently

### Phase 2: Environment Setup
1. Add environment variables to docker-compose.yml
2. Verify `requests` library in Odoo container
3. Create backup of current database

### Phase 3: Addon Installation (Controlled)
1. Copy addons to `/mnt/extra-addons` in container
2. Update module list in Odoo
3. Install `meta_leads` first (base functionality)
4. Install `webhooks_bridge` second (exposes endpoints)
5. Verify UI still works after each step

### Phase 4: Testing
1. Test webhook endpoints with curl
2. Send test webhook from Meta
3. Verify lead creation in CRM
4. Check UI remains responsive

## Recommended Safe Installation

### Option A: Isolated Testing (SAFEST)
Keep webhook system completely separate:
- Run in different directory with own Docker compose
- Use different database
- Test thoroughly before touching production Odoo

### Option B: Gradual Integration (RECOMMENDED)
1. Backup current Odoo database
2. Mount addons as separate volume (read-only first)
3. Install one module at a time
4. Test UI after each installation
5. Rollback if any issues

### Option C: Direct Integration (RISKY)
Install everything at once - NOT RECOMMENDED for production

## Rollback Plan

If anything goes wrong:
```bash
# Stop containers
docker compose down

# Remove volumes
docker volume rm crm_odoo-db-data crm_odoo-web-data

# Restart fresh (lose all data)
docker compose up -d
```

Or restore from backup if you made one.

## Next Actions Required

Before proceeding, you should:

1. **Choose integration approach** (A, B, or C above)
2. **Confirm you want to proceed** with webhook integration
3. **Decide on backup strategy** (full reset acceptable or need backup?)
4. **Test environment variables** are correctly set in .env

## Key Safety Rules

1. ✅ **ALWAYS backup before installing addons**
2. ✅ **Install one module at a time**
3. ✅ **Test UI after each change**
4. ✅ **Keep external scripts separate** (don't run in Odoo container)
5. ✅ **Use environment variables** (never hardcode credentials)
6. ✅ **Monitor logs** during installation
7. ✅ **Have rollback plan ready**

---

**Status**: Ready for your decision on which approach to take.
