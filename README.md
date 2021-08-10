# Aqara Gateway/Hub (G2H, M1S CN, P3 CN, M2 CN, H1 CN, E1 CN) integration for Home Assistant

Control Zigbee devices from Home Assistant with **Aqara Gateway (KTBL12LM, ZHWG15LM, ZHWG12LM, ZNSXJ12LM, ZNSXJ12LM)**.
Gateway support **Zigbee 3**.

This integration was based on the development of [@AlexxIT](https://github.com/AlexxIT/XiaomiGateway3/), Thanks Alex.

**ATTENTION:** The component **only works on modified firmware (M2) or the gateway which was enabled telnet.**

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

## Not Flash Custom firmware method

```shell
mkdir /data/bin
cd /data/bin
wget -O /data/bin/curl "http://master.dl.sourceforge.net/project/mgl03/bin/curl?viasf=1"
chmod +x /data/bin/curl
/data/bin/curl -s -k -L -o /data/bin/mosquitto https://raw.githubusercontent.com/niceboygithub/AqaraM1SM2fw/main/binutils/mosquitto
chmod a+x /data/bin/mosquitto

mkdir /data/scripts
cd /data/scripts
/data/bin/curl -s -k -L -o /data/scripts/post_init.sh https://raw.githubusercontent.com/niceboygithub/AqaraM1SM2fw/main/binutils/post_init.sh
chmod +x /data/scripts/post_init.sh
```
Then restart gateway by reboot command.

## Flash M1S Custom firmware method
```shell
cd /tmp && wget -O /tmp/curl "http://master.dl.sourceforge.net/project/mgl03/bin/curl?viasf=1" && chmod a+x /tmp/curl
/tmp/curl -s -k -L -o /tmp/m1s_update.sh https://raw.githubusercontent.com/niceboygithub/AqaraM1SM2fw/main/modified/M1S/m1s_update.sh
chmod a+x /tmp/m1s_update.sh && /tmp/m1s_update.sh
```
If there is no any error generated, then restart gateway by reboot command.

## Flash M2 Custom firmware method
```shell
cd /tmp && wget -O /tmp/curl "http://master.dl.sourceforge.net/project/mgl03/bin/curl?viasf=1" && chmod a+x /tmp/curl
/tmp/curl -s -k -L -o /tmp/m2_update.sh https://raw.githubusercontent.com/niceboygithub/AqaraM1SM2fw/main/modified/M2/m2_update.sh
chmod a+x /tmp/m2_update.sh && /tmp/m2_update.sh
```
If there is no any error generated, then restart gateway by reboot command.

## Flash P3 Custom firmware method
```shell
cd /tmp && wget -O /tmp/curl "http://master.dl.sourceforge.net/project/mgl03/bin/curl?viasf=1" && chmod a+x /tmp/curl
/tmp/curl -s -k -L -o /tmp/p3_update.sh https://raw.githubusercontent.com/niceboygithub/AqaraM1SM2fw/main/modified/P3/p3_update.sh
chmod a+x /tmp/p3_update.sh && /tmp/p3_update.sh
```
If there is no any error generated, then restart gateway by reboot command.

## Flash H1 Custom firmware method
```shell
cd /tmp && wget -O /tmp/curl "http://master.dl.sourceforge.net/project/mgl03/bin/curl?viasf=1" && chmod a+x /tmp/curl
/tmp/curl -s -k -L -o /tmp/h1_update.sh https://raw.githubusercontent.com/niceboygithub/AqaraM1SM2fw/main/modified/H1/h1_update.sh
chmod a+x /tmp/h1_update.sh && /tmp/h1_update.sh
```
If there is no any error generated, then restart gateway by reboot command.

## Flash E1 Custom firmware method

```shell
cd /tmp && wget -O /tmp/curl "http://master.dl.sourceforge.net/project/aqarahub/binutils/curl?viasf=1" && chmod a+x /tmp/curl
/tmp/curl -s -k -L -o /tmp/e1_update.sh https://raw.githubusercontent.com/niceboygithub/AqaraCameraHubfw/main/modified/E1/e1_update.sh
chmod a+x /tmp/e1_update.sh && /tmp/e1_update.sh
```
<img src="https://raw.githubusercontent.com/niceboygithub/AqaraGateway/master/E1_flash_done.png">

If there is no any error generated, then restart gateway by reboot command.

*Note: It updates firmware only if the checksum of the downloaded file is correct.*

## For G2H
There is a way to [enable telnetd](https://github.com/niceboygithub/AqaraCameraHubfw/blob/main/binutils/README.md#aqara-camera-hub-g2g2h-znsxj12lm-related-binutils).

## How to check this component is working properly.
Go to Configuration->Info->system_health
<img src="https://raw.githubusercontent.com/niceboygithub/AqaraGateway/master/system_health.png">


**Attention:** The component is under active development.

<a href="https://www.buymeacoffee.com/niceboygithub" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>
