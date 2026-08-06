%global name tcrm
%global unmangled_version %{version}
%global __requires_exclude ^.*tcrm/addons/mail/static/scripts/tcrm-mailgate.py$

Summary: tcrm Server
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: LGPL-3
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: tcrm S.A. <info@tcrm.com>
Requires: sassc
BuildRequires: python3-devel
BuildRequires: pyproject-rpm-macros
Url: https://www.tcrm.com

%description
tcrm is a complete ERP and CRM. The main features are accounting (analytic
and financial), stock management, sales and purchases management, tasks
automation, marketing campaigns, help desk, POS, etc. Technical features include
a distributed server, an object database, a dynamic GUI,
customizable reports, and XML-RPC interfaces.

%generate_buildrequires
%pyproject_buildrequires

%prep
%autosetup

%build
%py3_build

%install
%py3_install

%post
#!/bin/sh

set -e

tcrm_CONFIGURATION_DIR=/etc/tcrm
tcrm_CONFIGURATION_FILE=$tcrm_CONFIGURATION_DIR/tcrm.conf
tcrm_DATA_DIR=/var/lib/tcrm
tcrm_GROUP="tcrm"
tcrm_LOG_DIR=/var/log/tcrm
tcrm_LOG_FILE=$tcrm_LOG_DIR/tcrm-server.log
tcrm_USER="tcrm"

if ! getent passwd | grep -q "^tcrm:"; then
    groupadd $tcrm_GROUP
    adduser --system --no-create-home $tcrm_USER -g $tcrm_GROUP
fi
# Register "$tcrm_USER" as a postgres user with "Create DB" role attribute
su - postgres -c "createuser -d -R -S $tcrm_USER" 2> /dev/null || true
# Configuration file
mkdir -p $tcrm_CONFIGURATION_DIR
# can't copy debian config-file as addons_path is not the same
if [ ! -f $tcrm_CONFIGURATION_FILE ]
then
    echo "[options]
; This is the password that allows database operations:
; admin_passwd = admin
db_host = False
db_port = False
db_user = $tcrm_USER
db_password = False
addons_path = %{python3_sitelib}/tcrm/addons
default_productivity_apps = True
" > $tcrm_CONFIGURATION_FILE
    chown $tcrm_USER:$tcrm_GROUP $tcrm_CONFIGURATION_FILE
    chmod 0640 $tcrm_CONFIGURATION_FILE
fi
# Log
mkdir -p $tcrm_LOG_DIR
chown $tcrm_USER:$tcrm_GROUP $tcrm_LOG_DIR
chmod 0750 $tcrm_LOG_DIR
# Data dir
mkdir -p $tcrm_DATA_DIR
chown $tcrm_USER:$tcrm_GROUP $tcrm_DATA_DIR

INIT_FILE=/lib/systemd/system/tcrm.service
touch $INIT_FILE
chmod 0700 $INIT_FILE
cat << EOF > $INIT_FILE
[Unit]
Description=tcrm Open Source ERP and CRM
After=network.target

[Service]
Type=simple
User=tcrm
Group=tcrm
ExecStart=/usr/bin/tcrm --config $tcrm_CONFIGURATION_FILE --logfile $tcrm_LOG_FILE
KillMode=mixed

[Install]
WantedBy=multi-user.target
EOF

%files
%{_bindir}/tcrm
%{python3_sitelib}/%{name}-*.egg-info
%{python3_sitelib}/%{name}
%pycached %exclude %{python3_sitelib}/doc/cla/stats.py
%pycached %exclude %{python3_sitelib}/setup/*.py
%exclude %{python3_sitelib}/setup/tcrm

%changelog
* %{build_date} Christophe Monniez <moc@tcrm.com> - %{version}-%{release}
- Latest updates
