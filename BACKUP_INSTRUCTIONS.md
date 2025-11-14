
# Database Backup Instructions

## Before Installing Addons

### Option 1: Full Reset (Simple)
If you're okay losing current data and starting fresh:
```bash
docker compose down
docker volume rm crm_odoo-db-data crm_odoo-web-data
docker compose up -d
```

### Option 2: Database Backup (Preserve Data)
To backup your current database:

1. Access Odoo Database Manager:
   http://localhost:8069/web/database/manager
   
2. Enter master password: 69b7-e2u4-jypu

3. Click "Backup" next to 'crm' database

4. Download the backup file (crm_backup.zip)

5. Store safely before proceeding with addon installation

### Option 3: Docker Volume Backup
```bash
# Stop Odoo (keep volumes)
docker compose stop odoo

# Create backup
docker run --rm -v crm_odoo-db-data:/source -v C:/D/backups:/backup alpine tar czf /backup/odoo-db-backup.tar.gz -C /source .
docker run --rm -v crm_odoo-web-data:/source -v C:/D/backups:/backup alpine tar czf /backup/odoo-web-backup.tar.gz -C /source .

# Restart Odoo
docker compose start odoo
```

## Restoration

If something goes wrong:

### From Odoo Backup:
1. Go to: http://localhost:8069/web/database/manager
2. Click "Restore Database"
3. Upload your backup file
4. Enter master password and restore

### From Volume Backup:
```bash
docker compose down
docker volume rm crm_odoo-db-data crm_odoo-web-data
docker volume create crm_odoo-db-data
docker volume create crm_odoo-web-data
docker run --rm -v crm_odoo-db-data:/target -v C:/D/backups:/backup alpine tar xzf /backup/odoo-db-backup.tar.gz -C /target
docker run --rm -v crm_odoo-web-data:/target -v C:/D/backups:/backup alpine tar xzf /backup/odoo-web-backup.tar.gz -C /target
docker compose up -d
```
