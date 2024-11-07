# victron-dbus-tempcontrol
Read the internal temperature sensor of Victron Smartsolar MPPT. Control  the internal MPPT Relay based on temperature

# How to Install

- Login to Cerbo GX with ssh
- cd /data
- wget https://github.com/chriswg3/victron-dbus-tempcontrol/archive/refs/heads/main.zip
- unzip main.zip
- mv victron-dbus-tempcontrol-main dbus-tempcontrol
- cd dbus-tempcontrol
- Update config.ini (Set your personal settings, see below)
- chmod +x install.sh
- ./install.sh




# Configuration (config.ini)

# MPPT Tempcontrol Config
[DEFAULT]
# Count of MPPT's
mpptcount = 1
# Update in milliseconds
updateInterval = 60000

# Victron Name MPPT01, MPPT02...
[MPPT01]
# victron vrm id
deviceinstance=22
# id of smartsolar charger, list with dbus -y
id=com.victronenergy.solarcharger.socketcan_can0_vi0_uc123456
# control internal smartsolar relay
relayControl=True
# turn relay on temperature
onTemp = 30
# turn relay off temperature
offTemp = 25

# For every next smartsolar

#[MPPT02]
#deviceinstance=23
#id=com.victronenergy.solarcharger.socketcan_can0_vi1_uc234567
#relayControl=True
#onTemp = 30
#offTemp = 25

# How to uninstall

- cd /data/dbus-tempcontrol
- ./uninstall.sh
