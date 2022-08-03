# Aqara Gateway/Hub (G2H, M1S CN, P3 CN, M2 CN, H1 CN, E1 CN, G3 CN, G2H Pro) integration for Home Assistant

Control Zigbee devices from Home Assistant with **Aqara Gateway (KTBL12LM, ZHWG15LM, ZHWG12LM, ZNSXJ12LM, ZNSXJ12LM, ZNSXJ13LM, ZNSXJ15LM)**.
Gateway support **Zigbee 3**.

This integration was based on the development of [@AlexxIT](https://github.com/AlexxIT/XiaomiGateway3/), Thanks Alex.

**ATTENTION:** The component **only works on modified firmware (M2) or the gateway which was enabled telnet.**

**ATTENTION2**: The Lumi company (Aqara manufacturer) started disable the post_init script. If you still want to use this component, please do not update to latest firmware of the gateway/hub. If you already updated to latest firmware and telnet is not working, you need switch to Mi Home mode and enable telnet by soft_hack method. Then flash modified firmware.

For Gateway M2 and Switch H1 Hub, to flash modified firmware to M2, please use [AqaraGateway.exe](https://github.com/niceboygithub/AqaraM1SM2fw/raw/main/tools/aqaragateway.exe) to flash customize firmware. Need to open the case of gateway and wired out the UART of [M2](https://github.com/niceboygithub/AqaraM1SM2fw/raw/main/images/M2/m2_uart.png) or [H1](https://github.com/niceboygithub/AqaraM1SM2fw/raw/main/images/H1/h1_uart.png).

For Gateway M1S CN, AirCondition P3 CN, Hub E1 CN, please switch to **Mi Home mode**, and [get the token](https://github.com/piotrmachowski/xiaomi-cloud-tokens-extractor).

## Installation

you can install component with [HACS](https://hacs.xyz),  custom repo: HACS > Integrations > 3 dots (upper top corner) > Custom repositories > URL: `niceboygithub/AqaraGateway` > Category: Integration

Or Download and copy `custom_components/aqara_gateway` folder to `custom_components` folder in your HomeAssistant config folder


## Configuration

1. [⚙️ Configuration](https://my.home-assistant.io/redirect/config) > [🧩 Integrations](https://my.home-assistant.io/redirect/integrations) > [➕ Add Integration](https://my.home-assistant.io/redirect/config_flow_start?domain=aqara_gateway) > 🔍 Search `Aqara Gateway`

    Or click (HA v2021.3.0+): [![add](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=aqara_gateway)
   1. If the integration didn't show up in the list please REFRESH the page
   2. If the integration is still not in the list, you need to clear the browser cache.
2. Enter Gateway IP address.
3. If you applied a password of telnet in gateway, please enter the password. Otherwise, ignore this field.
4. Enter the xiaomi token of gateway if it is the first time to add integration. Otherwise, ignore this field.
5. Click Send button, then wait this integration is configured completely.
6. Done


[More detail instructions](https://gist.github.com/InsaneWookie/1221cd6267745ea3c16f6a2a83ba3a44) from [@InsaneWookie](https://gist.github.com/InsaneWookie)


## Manually Enable Telnet
You can use [custom open telnet command](https://gist.github.com/zvldz/1bd6b21539f84339c218f9427e022709) way 2 or way 3 to enable telnet in *Mija Home mode*, then flash modification firmwares to [M1S](https://github.com/niceboygithub/AqaraM1SM2fw/tree/main/modified/M1S), [P3](https://github.com/niceboygithub/AqaraM1SM2fw/tree/main/modified/P3), [E1](https://github.com/niceboygithub/AqaraCameraHubfw/tree/main/modified/E1),  if you want use them in Aqara Home. No need to open the case of gateway.

After telnet to gateway via putty, there are two methods (Flash or Not) to enable telnet and public mqtt.

## Not Flash modified firmware method (NOT for G2H, E1 hub, G3)

```shell
mkdir /data/bin
cd /data/bin
wget -O /data/bin/curl "http://master.dl.sourceforge.net/project/mgl03/bin/curl?viasf=1"; chmod +x /data/bin/curl
/data/bin/curl -s -k -L -o /data/bin/mosquitto https://raw.githubusercontent.com/niceboygithub/AqaraM1SM2fw/main/binutils/mosquitto; chmod a+x /data/bin/mosquitto

mkdir /data/scripts
cd /data/scripts
/data/bin/curl -s -k -L -o /data/scripts/post_init.sh https://raw.githubusercontent.com/niceboygithub/AqaraM1SM2fw/main/binutils/post_init.sh
chmod +x /data/scripts/post_init.sh
```
Then restart gateway by reboot command.

## Not Flash modified firmware method (for G2H)

```shell
mkdir /data/bin
cd /data/bin
wget -O /tmp/curl "http://master.dl.sourceforge.net/project/aqarahub/binutils/curl?viasf=1"; chmod +x /tmp/curl
/tmp/curl -s -k -L -o /data/bin/mosquitto https://raw.githubusercontent.com/niceboygithub/AqaraCameraHubfw/main/binutils/mosquitto; chmod a+x /data/bin/mosquitto

```

## Not Flash modified firmware method (for G2H)

```shell
mkdir /data/bin
cd /data/bin
wget -O /tmp/curl "http://master.dl.sourceforge.net/project/aqarahub/binutils/curl?viasf=1"; chmod +x /tmp/curl
/tmp/curl -s -k -L -o /data/bin/mosquitto https://raw.githubusercontent.com/niceboygithub/AqaraCameraHubfw/main/binutils/mosquitto_g2hpro; chmod a+x /data/bin/mosquitto

```

## Not Flash modified firmware method (for E1 hub, G3)

```shell
mkdir /data/bin
cd /data/bin
wget -O /tmp/curl "http://master.dl.sourceforge.net/project/aqarahub/binutils/curl?viasf=1"; chmod +x /tmp/curl
/tmp/curl -s -k -L -o /data/bin/mosquitto https://raw.githubusercontent.com/niceboygithub/AqaraCameraHubfw/main/binutils/mosquitto_e1; chmod a+x /data/bin/mosquitto

```

## Flash M1S modified firmware method
```shell
cd /tmp && wget -O /tmp/curl "http://master.dl.sourceforge.net/project/mgl03/bin/curl?viasf=1" && chmod a+x /tmp/curl
/tmp/curl -s -k -L -o /tmp/m1s_update.sh https://raw.githubusercontent.com/niceboygithub/AqaraM1SM2fw/main/modified/M1S/m1s_update.sh
chmod a+x /tmp/m1s_update.sh && /tmp/m1s_update.sh
```
If there is no any error generated, then restart gateway by reboot command.

## Flash M2 modified firmware method
```shell
cd /tmp && wget -O /tmp/curl "http://master.dl.sourceforge.net/project/mgl03/bin/curl?viasf=1" && chmod a+x /tmp/curl
/tmp/curl -s -k -L -o /tmp/m2_update.sh https://raw.githubusercontent.com/niceboygithub/AqaraM1SM2fw/main/modified/M2/m2_update.sh
chmod a+x /tmp/m2_update.sh && /tmp/m2_update.sh
```
If there is no any error generated, then restart gateway by reboot command.

## Flash P3 modified firmware method
```shell
cd /tmp && wget -O /tmp/curl "http://master.dl.sourceforge.net/project/mgl03/bin/curl?viasf=1" && chmod a+x /tmp/curl
/tmp/curl -s -k -L -o /tmp/p3_update.sh https://raw.githubusercontent.com/niceboygithub/AqaraM1SM2fw/main/modified/P3/p3_update.sh
chmod a+x /tmp/p3_update.sh && /tmp/p3_update.sh
```
If there is no any error generated, then restart gateway by reboot command.

## Flash H1 modified firmware method
```shell
cd /tmp && wget -O /tmp/curl "http://master.dl.sourceforge.net/project/mgl03/bin/curl?viasf=1" && chmod a+x /tmp/curl
/tmp/curl -s -k -L -o /tmp/h1_update.sh https://raw.githubusercontent.com/niceboygithub/AqaraM1SM2fw/main/modified/H1/h1_update.sh
chmod a+x /tmp/h1_update.sh && /tmp/h1_update.sh
```
If there is no any error generated, then restart gateway by reboot command.

## Not Flash E1 modified firmware method

Suggest to use another expert's method, pleae move to [his github](https://github.com/zvldz/aqcn02_fw/tree/main/update) to see hot to do it.  He provides a way that avoid any risk on flashing firmwares.

If there is no any error generated, then restart gateway by reboot command.

*Note: It updates firmware only if the checksum of the downloaded file is correct.*

## For G2H
There is a way to [enable telnetd](https://github.com/niceboygithub/AqaraCameraHubfw/blob/main/binutils/README.md#aqara-camera-hub-g2g2h-znsxj12lm-related-binutils).

## For G3
There is a way to [enable telnetd](https://github.com/Wh1terat/aQRootG3) from #Wh1terat. After enabled telnet, you need use putty to telnet <ip of your G3>. Then enter the following commands.

```
chmod a+w /data/scripts/post_init.sh
echo -e "#!/bin/sh\n\nasetprop sys.camera_ptz_moving true\nfw_manager.sh -r\nfw_manager.sh -t -k" > /data/scripts/post_init.sh
chattr +i post_init.sh
```

Due to [Lumi closed the exploit](https://github.com/Wh1terat/aQRootG3#warningwarning-warning) and removed post_init.sh feature after version 3.4.1. It won't support after the version 3.3.9 of G3 firmware. If you want to enable telnet of G3, you need to downgrade the firmware to the version 3.3.4. The method to downgrade is as the following steps.

```
1. Get 'rootfs.bin' of firmware version 3.3.4. (use 7z to extract the firmware bin)
2. Copy 'rootfs.bin' to sdcard which is using FAT32 format.
3. Power Off G3.
4. Insert the sdcard to G3.
5. Press the front button of G3.
6. Power on G3.
7. Wait three seconds and release the button.
8. If the LED is turned to RED, it starts to flash 'rootfs.bin'.
```

**Important:** Aqara may force your G3 to upgrade to latest without your permission. To lock firmware update, please use below commands to lock by telnet.
```
mkdir -p /data/ota_dir
touch /data/ota_dir/lumi_fw.tar
chattr +i /data/ota_dir/lumi_fw.tar
```


## How to check this component is working properly.
Go to Configuration->Info->system_health
<img src="https://raw.githubusercontent.com/niceboygithub/AqaraGateway/master/system_health.png">


### Aqara Presence Detector FP1

Movements sensor
```
In the left and right monitoring mode, only report 2, 3, 4, 5, 6, 7;
In the non-directional monitoring mode, only report 0, 1, 6, 7; 0: enter 1: leave 2: left in 3: right out 4 : Right in 5: Left out 6: Approaching 7: Far away
```

**Attention:** The component is under active development.

<a href="https://www.buymeacoffee.com/niceboygithub" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>
