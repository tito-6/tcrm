# TCRM - Total CRM Management System

## Current Status
TCRM is a comprehensive white-labeling and integration solution built on Odoo 18. The system has been fully rebranded to TCRM, removing "Odoo" references and applying a modern, high-contrast design system.

### Key Features
- **Global White-Labeling**: Complete rebranding of the Odoo interface (Login, Dashboard, Menus, "About" dialog).
- **Brand Identity**:
  - **Colors**: Deep Blue (#1C1E59), TCRM Red (#EA0000), Dark Slate (#0E142C).
  - **Typography**: "Bricolage Grotesque" font integrated globally.
- **Integrations**:
  - **Meta Lead Integration**: Automated fetching and mapping of Facebook/Instagram leads into CRM.
  - **WhatsApp Business Integration**: Native WhatsApp messaging within Odoo records.
- **Custom CRM Enhancements**: Responsive lead views and specialized data handling.

## Setup Instructions

### Prerequisites
- Docker & Docker Compose
- Git

### Installation
1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/tito-6/tcrm.git
    cd tcrm
    ```

2.  **Environment Configuration**:
    Copy the example environment file and adjust the variables if necessary (DB passwords, etc.):
    ```bash
    cp .env.example .env
    ```

3.  **Start the System**:
    ```bash
    docker-compose up -d
    ```

4.  **First Access**:
    - URL: `http://localhost:8069`
    - The `theme_tcrm` module is set to `auto_install=True` and will apply branding once dependencies are met.

## Project Structure
- `custom-addons/`: Contains all TCRM-specific modules (`theme_tcrm`, `whatsapp_business_integration`, etc.).
- `config/`: System configuration files (odoo.conf).
- `nginx/`: Reverse proxy configuration.
- `docker-compose.yml`: Container orchestration setup.

## Running the Project
The project uses Docker for a self-contained environment.
- **Start**: `docker-compose up -d`
- **Stop**: `docker-compose down`
- **Logs**: `docker-compose logs -f odoo`
- **Update Modules**: `docker-compose run --rm odoo odoo -u theme_tcrm,whatsapp_business_integration -d <your-db> --stop-after-init`

---
*Developed by TCRM Team*
