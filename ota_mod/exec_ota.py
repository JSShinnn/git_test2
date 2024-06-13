import json
from ota_mod import ota
from ota_mod.ota import OTAUpdater
from WIFI_CONFIG import SSID, PASSWORD, FIRMWARE_URL

#firmware_url = FIRMWARE_URL
filename = "firmware.py"

def get_ssid_pw():
    with open('ssid.json', 'r') as file:
        # 파일 내용 읽기
        content = file.read()
    data = json.loads(content)
    return data['ssid'], data['pw']

idpw = get_ssid_pw()

print(idpw[0])
print(idpw[1])


firmware_url = FIRMWARE_URL
#firmware_url = "https://raw.githubusercontent.com/SGbiohealth/studystraight-fw/main/"

ota_updater = OTAUpdater(idpw[0], idpw[1], firmware_url, filename)

def ota_ethnet():
    ota_updater.download_and_install_update_if_available()

def ota_update():
    # FIRMWARE_URL 폴더 내에 "firmware.py의 파일이 펌웨어 파일이 됨"
    ota_updater.download_and_install_update_if_available()
    
def ota_update_ugit():
    # FIRMWARE_URL 폴더 내에 "firmware.py의 파일이 펌웨어 파일이 됨"
    return ota_updater.download_and_install_update_if_available_for_ugit()
    
def ota_update_version():
    # FIRMWARE_URL 폴더 내에 "firmware.py의 파일이 펌웨어 파일이 됨"
    ota_updater.update_version()

def ota_disconnect():
    ota_updater.Disconnect_wifi()

def ota_connect():
    ota_updater.connect_wifi()

def get_ssid_pw():
    with open('ssid.json', 'r') as file:
        # 파일 내용 읽기
        content = file.read()
    data = json.loads(content)
    return data['ssid'], data['pw']

def chg_ssid_pw(msg) :
    input_string = msg
    ssid_value=''
    pw_value=''
    
    index_of_comma = input_string.find(',')
    
    if index_of_comma != -1:
        ssid_value = input_string[len("^SPW"):index_of_comma]
        pw_value = input_string[index_of_comma + 1:]
        print("첫 번째 변수:", ssid_value)
        print("두 번째 변수:", pw_value)

    with open('ssid.json', 'r') as file:
        # 파일 내용 읽기
        content = file.read()
    
    data = json.loads(content)

    if 'ssid' in data:
        data['ssid'] =''
        data['ssid'] = ssid_value
    if 'pw' in data:
        data['pw'] =''
        data['pw'] = pw_value
        print("\nValue corresponding to 'ssid' key:", ssid_value , ", pw:", pw_value)

    # 수정된 내용을 SSID_PW.json 파일에 다시 쓰기
    with open('ssid.json', 'w') as file:
        data = json.dumps(data)
        result = file.write(data)

    with open('ssid.json', 'r') as file:
        content = file.read()

    data = json.loads(content)

    if 'ssid' in data:
        ssid_value2 = data['ssid']
    if 'pw' in data:           
        pw_value2 = data['pw']
        
    if ssid_value == ssid_value2 and pw_value == pw_value2:
        return True
    else:
        return False
