# Aqara Gateway/Hub (G2H, M1S CN, P3 CN, M2) integration for Home Assistant

Control Zigbee devices from Home Assistant with **Aqara Gateway (KTBL12LM, ZHWG15LM, ZHWG12LM, ZNSXJ12LM)**.
Gateway support **Zigbee 3**.

This integration was based on the development of <a href=https://github.com/AlexxIT/XiaomiGateway3/>@AlexxIT</a>, Thanks Alex.

**ATTENTION:** The component **only works on modified firmware (M2) or the gateway which enabled telnet.**

For Gateway M2, to flash modified firmware to M2, please use <a href="https://github.com/niceboygithub/AqaraM1SM2fw/raw/main/tools/aqaragateway.exe"> AqaraGateway.exe </a> to flash customize firmware. Need to open the case of gateway and wired out the UART.

For Gateway M1S CN, AirCondition P3, Smart Hub H1, please switch to **Mija Home mode**, and [get the token](https://github.com/piotrmachowski/xiaomi-cloud-tokens-extractor). Then install this integration by HACS. After installation, add this componment via GUI integration of Home Assistant. Or you can use <a href="https://gist.github.com/zvldz/1bd6b21539f84339c218f9427e022709"> custom open telnet command </a> way 2 or way 3 to enable telnet in *Mija Home mode*, then flash modification firmwares to <a href="https://github.com/niceboygithub/AqaraM1SM2fw/tree/main/modified/M1S"> M1S </a>, <a href="https://github.com/niceboygithub/AqaraM1SM2fw/tree/main/modified/P3"> P3 </a> if you want use them in Aqara Home.No need to open the case of gateway.

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
cd /tmp
wget -O /tmp/curl "http://master.dl.sourceforge.net/project/mgl03/bin/curl?viasf=1"
chmod a+x /tmp/curl
/tmp/curl -s -k -L -o /tmp/linux.bin https://github.com/niceboygithub/AqaraM1SM2fw/blob/main/original/M1S/3.2.4_0014.0520_mi_fw_ver_3.1.3_0011/linux_3.2.4_0014.0520_mi_fw_ver_3.1.3_0011.bin
fw_update /tmp/linux.bin
/tmp/curl -s -k -L -o /tmp/rootfs.bin https://github.com/niceboygithub/AqaraM1SM2fw/blob/main/modified/M1S/3.2.4_0014.0520_mi_fw_ver_3.1.3_0011/rootfs_3.2.4_0014.0520_mi_fw_ver_3.1.3_0011_modification.bin
fw_update /tmp/rootfs.bin
```
Then restart gateway by reboot command.

## Flash P3 Custom firmware method
```shell
cd /tmp
wget -O /tmp/curl "http://master.dl.sourceforge.net/project/mgl03/bin/curl?viasf=1"
chmod a+x /tmp/curl
/tmp/curl -s -k -L -o /tmp/linux.bin https://raw.githubusercontent.com/niceboygithub/AqaraM1SM2fw/main/original/P3/3.0.7_0007.0515/linux_3.0.7_0007.0515.bin
fw_update /tmp/linux.bin
/tmp/curl -s -k -L -o /tmp/rootfs.bin https://raw.githubusercontent.com/niceboygithub/AqaraM1SM2fw/main/modified/P3/3.0.7_0007.0515/rootfs_3.0.7_0007.0515_modified.bin
fw_update /tmp/rootfs.bin
```
Then restart gateway by reboot command.

## Flash H1 Custom firmware method
```shell
cd /tmp
wget -O /tmp/curl "http://master.dl.sourceforge.net/project/mgl03/bin/curl?viasf=1"
chmod a+x /tmp/curl
/tmp/curl -s -k -L -o /tmp/linux.bin https://github.com/niceboygithub/AqaraM1SM2fw/blob/main/original/H1/3.0.8_0001.0512/linux_3.0.8_0001.0512.bin
fw_update /tmp/linux.bin
/tmp/curl -s -k -L -o /tmp/rootfs.bin https://github.com/niceboygithub/AqaraM1SM2fw/blob/main/modified/H1/3.0.8_0001.0512/rootfs_3.0.8_0001.0512_modified.bin
fw_update /tmp/rootfs.bin
```
Then restart gateway by reboot command.

For G2H, there is way to <a href="https://github.com/niceboygithub/AqaraCameraHubfw/blob/main/binutils/README.md#aqara-camera-hub-g2g2h-znsxj12lm-related-binutils">enable telnetd</a>.

## How to check this component is working properly.
Go to Configuration->Info->system_health
<img src="https://github.com/niceboygithub/AqaraGateway/blob/master/system_health.png">


**Attention:** The component is under active development.

<a href="https://www.buymeacoffee.com/niceboygithub" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>
