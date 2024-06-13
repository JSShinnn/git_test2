from WIFI_CONFIG import SSID, PASSWORD, FIRMWARE_URL
import ota_mod.exec_ota as ota

ota.ota_update()

#ota.ota_update(FIRMWARE_URL, "firmware.py")
#ota.ota_disconnect()
#ota.ota_connect()