# Aqara Gateway/Hub (G2H, M1S CN, M2) integration for Home Assistant

Control Zigbee devices from Home Assistant with **Aqara Gateway (ZHWG15LM, ZHWG12LM, ZNSXJ12LM)**.

This integration was based on the development of <a href=https://github.com/AlexxIT/XiaomiGateway3/>@AlexxIT</a>, Thanks Alex.

**ATTENTION:** The component **only works on modified firmware (M1S, M2). **

To flash modified firmware, please use <a href="https://github.com/niceboygithub/AqaraM1SM2fw/raw/main/tools/aqaragateway.exe"> AqaraGateway.exe </a> to flash. Need to open the case of gateway and wired out the UART.

For M1S CN, you can use <a href="https://gist.github.com/zvldz/1bd6b21539f84339c218f9427e022709"> custom open telnet command </a> way 2 or way 3 to enable telnet, then flash modification firmwares. No need to open the case of gateway.

For G2H, you need to wired out the UART, then login to gateway to <a href="https://github.com/niceboygithub/AqaraCameraHubfw/tree/main/binutils#aqara-camera-hub-g2g2h-znsxj12lm-related-binutils">enable telnetd</a>.

Gateway support **Zigbee 3**.

**Attention:** The component is under active development.

<a href="https://www.buymeacoffee.com/niceboygithub" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="41" width="174"></a>
