#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail
# set -o xtrace

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
__file="${__dir}/$(basename "${BASH_SOURCE[0]}")"
__base="$(basename ${__file} .sh)"

# Recommends: antiword, graphviz, ghostscript, python-gevent, poppler-utils
export DEBIAN_FRONTEND=noninteractive

# single-user mode, appropriate for chroot environment
# explicitly setting the runlevel prevents warnings after installing packages
export RUNLEVEL=1

# Unset lang variables to prevent locale settings leaking from host
unset "${!LC_@}"
unset "${!LANG@}"

# set locale to en_US
echo "set locale to en_US"
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
dpkg-reconfigure locales

# Aliases
echo  "alias ll='ls -al'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias tcrm='sudo systemctl stop tcrm; sudo -u tcrm /usr/bin/python3 /home/pi/tcrm/tcrm-bin --config /home/pi/tcrm.conf'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias tcrm_logs='less -R +F /var/log/tcrm/tcrm-server.log'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias tcrm_conf='cat /home/pi/tcrm.conf'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias install='sudo chroot /root_bypass_ramdisks/'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias blackbox='ls /dev/serial/by-path/'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias nano='sudo -u tcrm nano -l'" | tee -a /home/pi/.bashrc
echo  "alias vim='sudo -u tcrm vim -u /home/pi/.vimrc'" | tee -a /home/pi/.bashrc
echo  "alias tcrm_luxe='printf \" ______\n< Luxe >\n ------\n        \\   ^__^\n         \\  (oo)\\_______\n            (__)\\       )\\/\\ \n                ||----w |\n                ||     ||\n\"'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias tcrm_start='sudo systemctl start tcrm'" >> /home/pi/.bashrc
echo  "alias tcrm_stop='sudo systemctl stop tcrm'" >> /home/pi/.bashrc
echo  "alias tcrm_restart='sudo systemctl restart tcrm'" >> /home/pi/.bashrc
echo "
tcrm_help() {
  echo '-------------------------------'
  echo ' Welcome to Tcrm IoT Box tools'
  echo '-------------------------------'
  echo ''
  echo 'tcrm                  Starts/Restarts Tcrm server manually (not through tcrm.service)'
  echo 'tcrm_logs             Displays Tcrm server logs in real time'
  echo 'tcrm_conf             Displays Tcrm configuration file content'
  echo 'install               Bypasses ramdisks to allow package installation'
  echo 'blackbox              Lists all serial connected devices'
  echo 'tcrm_start            Starts Tcrm service'
  echo 'tcrm_stop             Stops Tcrm service'
  echo 'tcrm_restart          Restarts Tcrm service'
  echo 'tcrm_dev <branch>     Resets Tcrm on the specified branch from tcrm-dev repository'
  echo 'tcrm_origin <branch>  Resets Tcrm on the specified branch from the tcrm repository'
  echo 'devtools              Enables/Disables specific functions for development (more help with devtools help)'
  echo ''
  echo 'Tcrm IoT online help: <https://www.tcrm.com/documentation/latest/applications/general/iot.html>'
}

tcrm_dev() {
  if [ -z \"\$1\" ]; then
    tcrm_help
    return
  fi
  pwd=\$(pwd)
  cd /home/pi/tcrm
  sudo -u tcrm git remote add dev https://github.com/tcrm-dev/tcrm.git
  sudo -u tcrm git fetch dev \$1 --depth=1 --prune
  sudo -u tcrm git reset --hard FETCH_HEAD
  sudo -u tcrm git branch -m \$1
  sudo chroot /root_bypass_ramdisks /bin/bash -c \"export DEBIAN_FRONTEND=noninteractive && xargs apt-get -y -o Dpkg::Options::=\"--force-confdef\" -o Dpkg::Options::=\"--force-confold\" install < /home/pi/tcrm/addons/iot_box_image/configuration/packages.txt\"
  sudo -u tcrm pip3 install -r /home/pi/tcrm/addons/iot_box_image/configuration/requirements.txt --break-system-package
  cd \$pwd
}

tcrm_origin() {
  if [ -z \"\$1\" ]; then
    tcrm_help
    return
  fi
  pwd=\$(pwd)
  cd /home/pi/tcrm
  sudo -u tcrm git remote set-url origin https://github.com/tcrm/tcrm.git  # ensure tcrm repository
  sudo -u tcrm git fetch origin \$1 --depth=1 --prune
  sudo -u tcrm git reset --hard FETCH_HEAD
  sudo -u tcrm git branch -m \$1
  sudo chroot /root_bypass_ramdisks /bin/bash -c \"export DEBIAN_FRONTEND=noninteractive && xargs apt-get -y -o Dpkg::Options::=\"--force-confdef\" -o Dpkg::Options::=\"--force-confold\" install < /home/pi/tcrm/addons/iot_box_image/configuration/packages.txt\"
  sudo -u tcrm pip3 install -r /home/pi/tcrm/addons/iot_box_image/configuration/requirements.txt --break-system-package
  cd \$pwd
}

pip() {
  if [[ -z \"\$1\" || -z \"\$2\" ]]; then
    tcrm_help
    return 1
  fi
  additional_arg=\"\"
  if [ \"\$1\" == \"install\" ]; then
    additional_arg=\"--user\"
  fi
  pip3 \"\$1\" \"\$2\" --break-system-package \$additional_arg
}

devtools() {
  help_message() {
    echo 'Usage: devtools <enable/disable> <general/actions> [action name]'
    echo ''
    echo 'Only provide an action name if you want to enable/disable a specific device action.'
    echo 'If no action name is provided, all actions will be enabled/disabled.'
    echo 'To enable/disable multiple actions, enclose them in quotes separated by commas.'
  }
  case \"\$1\" in
    enable|disable)
      case \"\$2\" in
        general|actions|longpolling)
          if ! grep -q '^\[devtools\]' /home/pi/tcrm.conf; then
            sudo -u tcrm bash -c \"printf '\n[devtools]\n' >> /home/pi/tcrm.conf\"
          fi
          if [ \"\$1\" == \"disable\" ]; then
            value=\"\${3:-*}\" # Default to '*' if no action name is provided
            devtools enable \"\$2\" # Remove action/general/longpolling from conf to avoid duplicate keys
            sudo sed -i \"/^\[devtools\]/a\\\\\$2 = \$value\" /home/pi/tcrm.conf
          elif [ \"\$1\" == \"enable\" ]; then
            sudo sed -i \"/\[devtools\]/,/\[/{/\$2 =/d}\" /home/pi/tcrm.conf
          fi
          ;;
        *)
          help_message
          return 1
          ;;
      esac
      ;;
    *)
      help_message
      return 1
      ;;
  esac
}
" | tee -a ~/.bashrc /home/pi/.bashrc

# Change default hostname from 'raspberrypi' to 'iotbox'
echo iotbox | tee /etc/hostname
sed -i 's/\braspberrypi/iotbox/g' /etc/hosts

apt-get update

# At the first start it is necessary to configure a password
# This will be modified by a unique password on the first start of Tcrm
password="$(openssl rand -base64 12)"
echo "pi:${password}" | chpasswd
echo TrustedUserCAKeys /etc/ssh/ca.pub >> /etc/ssh/sshd_config

# Prevent Wi-Fi blocking
apt-get -y remove rfkill

echo "Acquire::Retries "16";" > /etc/apt/apt.conf.d/99acquire-retries
# KEEP OWN CONFIG FILES DURING PACKAGE CONFIGURATION
# http://serverfault.com/questions/259226/automatically-keep-current-version-of-config-files-when-apt-get-install
xargs apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install < /home/pi/tcrm/addons/iot_box_image/configuration/packages.txt
apt-get -y autoremove

apt-get clean
localepurge
rm -rfv /usr/share/doc

# Remove the default nginx website, we have our own config in /etc/nginx/conf.d/
rm /etc/nginx/sites-enabled/default

pip3 install -r /home/pi/tcrm/addons/iot_box_image/configuration/requirements.txt --break-system-package

# Create Tcrm user for tcrm service and disable password login
adduser --disabled-password --gecos "" --shell /usr/sbin/nologin tcrm

# tcrm user doesn't need to type its password to run sudo commands
cp /etc/sudoers.d/010_pi-nopasswd /etc/sudoers.d/010_tcrm-nopasswd
sed -i 's/pi/tcrm/g' /etc/sudoers.d/010_tcrm-nopasswd

# copy the tcrm.conf file to the overwrite directory
mv -v "/home/pi/tcrm/addons/iot_box_image/configuration/tcrm.conf" "/home/pi/"
chown tcrm:tcrm "/home/pi/tcrm.conf"

groupadd usbusers
usermod -a -G usbusers tcrm
usermod -a -G video tcrm
usermod -a -G render tcrm
usermod -a -G lp tcrm
usermod -a -G input tcrm
usermod -a -G dialout tcrm
usermod -a -G pi tcrm
mkdir -v /var/log/tcrm
chown tcrm:tcrm /var/log/tcrm
chown tcrm:tcrm -R /home/pi/tcrm/

# logrotate is very picky when it comes to file permissions
chown -R root:root /etc/logrotate.d/
chmod -R 644 /etc/logrotate.d/
chown root:root /etc/logrotate.conf
chmod 644 /etc/logrotate.conf

update-rc.d -f hostapd remove
update-rc.d -f nginx remove
update-rc.d -f dnsmasq remove

systemctl enable ramdisks.service
systemctl disable dphys-swapfile.service
systemctl enable ssh
systemctl set-default graphical.target
systemctl disable getty@tty1.service
systemctl disable systemd-timesyncd.service
systemctl unmask hostapd.service
systemctl disable hostapd.service
systemctl disable cups-browsed.service
systemctl enable labwc.service
systemctl enable tcrm.service
systemctl enable tcrm-led-manager.service
systemctl enable tcrm-ngrok.service

# create dirs for ramdisks
create_ramdisk_dir () {
    mkdir -v "${1}_ram"
}

create_ramdisk_dir "/var"
create_ramdisk_dir "/etc"
create_ramdisk_dir "/tmp"
mkdir -v /root_bypass_ramdisks

echo ""
echo "--- DEFAULT PASSWORD: ${password} ---"
echo ""
