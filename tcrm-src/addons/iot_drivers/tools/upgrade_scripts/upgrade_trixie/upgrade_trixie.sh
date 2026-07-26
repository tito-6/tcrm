#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

sudo mount -o remount,rw / && sudo mount -o remount,rw /root_bypass_ramdisks

logfile=/home/pi/upgrade.log
sudo touch "$logfile"
exec 3>&1 4>&2
trap 'exec 2>&4 1>&3' 0 1 2 3
exec > >(sudo tee -a "$logfile") 2>&1  # Print to stdout and logfile
set -x                            # display commands before execution

# Commands to upgrade IoT 25.07 to Raspbian 13 Trixie

# Setup chroot
cd /root_bypass_ramdisks/
sudo mount -t proc /proc proc/
sudo mount -t sysfs /sys sys/
sudo mount --rbind /dev dev/

# Use hw_drivers if present, otherwise fall back to iot_drivers
SCRIPT_PATH=/home/pi/tcrm/addons/iot_drivers/tools/upgrade_scripts/upgrade_trixie/upgrade_trixie_chroot.sh

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Upgrade script not found at $SCRIPT_PATH" >&2
    exit 1
fi

sudo chroot /root_bypass_ramdisks/ "$SCRIPT_PATH"

# Checkout saas-19.1 (if >= 19.1 is needed the iot box will checkout again to the required version on start)
cd /home/pi/tcrm
sudo -u tcrm git remote set-url origin https://github.com/tcrm/tcrm.git
sudo -u tcrm git fetch origin saas-19.1 --depth=1 --prune
sudo -u tcrm git reset --hard FETCH_HEAD
sudo -u tcrm git branch -m saas-19.1

# Copy service scripts to /hw_
sudo cp /home/pi/tcrm/setup/iot_box_builder/overwrite_after_init/etc/setup_ramdisks.sh /root_bypass_ramdisks/etc/setup_ramdisks.sh
sudo cp /home/pi/tcrm/setup/iot_box_builder/overwrite_after_init/etc/led_manager.sh /root_bypass_ramdisks/etc/led_manager.sh

# Reinstall PIP packages
sudo mount -o remount,rw / && sudo mount -o remount,rw /root_bypass_ramdisks
sudo -u tcrm pip install --break-system-packages -r /home/pi/tcrm/setup/iot_box_builder/configuration/requirements.txt

# Ensure iot drivers are used in tcrm.conf
sudo sed -i 's|^server_wide_modules *=.*|server_wide_modules = iot_drivers,web|' /home/pi/tcrm.conf

set +x

# Reboot
sudo reboot
