import requests
import json

import RPi.GPIO as GPIO
import numpy as np
from datetime import datetime, timezone

from time import sleep
import os
import datetime

from enum import Enum

import socket
from _thread import *

import logging
from logging.handlers import TimedRotatingFileHandler

import serial
import re

import urllib.request

import subprocess

import zipfile


#Log 설정
####################################################################################################################################
# Ensure the directory exists
log_directory = '/home/pi/mu_code/log/'

if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Update the filename to include the log directory
filename = os.path.join(log_directory, 'rain.log')

# Log settings
rainLogFormatter = logging.Formatter('%(asctime)s, %(message)s')

# Handler settings
rainLogHandler = TimedRotatingFileHandler(filename=filename, when='midnight', interval=1, encoding='utf-8')
rainLogHandler.setFormatter(rainLogFormatter)
rainLogHandler.suffix = "%Y%m%d"

# Logger set
rainLogger = logging.getLogger('rainLogger')
rainLogger.setLevel(logging.INFO)
rainLogger.addHandler(rainLogHandler)

rainLogger.info("This is a test log message.")

#강수량 측정
rain = 15

#LED관련
ledG_Internet = 27
ledR_Error = 26
ledB_Ex = 13
ledB_Standby= 25

tick_CNT=0
CNT_num=0

UUID =''

#GPIO
GPIO.setmode(GPIO.BCM)

#rain 게이지(new version is PUD_UP)
GPIO.setup(rain, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#set LED
GPIO.setup(ledB_Standby, GPIO.OUT)
GPIO.setup(ledG_Internet, GPIO.OUT)
GPIO.setup(ledR_Error, GPIO.OUT)
GPIO.setup(ledB_Ex, GPIO.OUT)

before_Sec=0
before_Min=0
#Before_Mode = 0
Now_Mode = ''
device_MAC = ''

_Init = ('init')
_Idle = ('idle')
_Ex = ('Ex')
_Error = ('Error')


def InitSys():
    
        global log_directory, before_Min, UUID, device_MAC, Now_Mode
        
        print("Init Sys....")
        Now_Mode = _Init
        GPIO.output(ledG_Internet, True)   
        GPIO.output(ledR_Error, True)   
        GPIO.output(ledB_Standby, True)
        
        #led 초기화
        GPIO.output(ledG_Internet, False)   
        GPIO.output(ledR_Error, False)

        delete_old_logs(log_directory)
        
        now = datetime.datetime.now()
        before_Min = now.minute
        
        UUID = get_uuid()
        print(UUID)

        if not check_internet_connection():
            GPIO.output(ledG_Internet, False)
            Now_Mode = _Error
        else:
            GPIO.output(ledG_Internet, True)

            if check_server_connection():
                print("ota server Succ")
                os.chdir('/home/pi/mu_code/')
                check_ota()
            else:
                print("ota server fail")
        
            #UUID 가져오기
            if UUID =='':
                if not send_macaddress():
                    Now_Mode = _Error
            else:
                print("passed uuid check")
                #integrity check
                if not send_integrity(device_MAC):
                    if not send_integrity(device_MAC):
                        if not send_integrity(device_MAC):
                            print("Error integrity check!")
                            Now_Mode = _Error
            print("passed uuid and integrity check!")
            rainLogger.info("finished init")
            Now_Mode = _Idle
            
        checkMode()

        
def get_cpu_temperature():
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as file:
            temp_str = file.read().strip()
            temp_c = int(temp_str) / 1000.0  # 온도를 밀리도 단위에서 섭씨도로 변환
            return temp_c
    except FileNotFoundError:
        print("Error: The temperature file was not found.")
        return None
    except IOError as e:
        print(f"Error: An I/O error occurred while reading the temperature file: {e}")
        return None
    except ValueError as e:
        print(f"Error: Could not convert the temperature value to an integer: {e}")
        return None


def send_integrity(MacAddress):
    global UUID, Now_Mode
    Now_Mode = _Ex
    checkMode()
    current_date = datetime.datetime.now()
    formatted_time = current_date.strftime("%Y-%m-%d %H:%M:%S")
    url = "http://svcrg.gb-on.co.kr/raingauge/reboot"
    data = {
        'equipUuid' : UUID,
        'startDatetime': formatted_time,
        'macaddress': MacAddress
    }
    
    print(data)
    
    # JSON 데이터를 문자열로 변환
    json_data = json.dumps(data)
    
    # TODO: Try-catch

    response = requests.post(url, data=json_data, headers={'Content-Type': 'application/json'})

    data = response.json()
    
    # 응답 확인
    if response.status_code == 200:
        rainLogger.info("post integrit uuid:%s, mac:%s, %s" % (UUID,MacAddress, response.text))
        print("Response is :", response.text)
        return True
        #os.system('sudo reboot')
    else:
        rainLogger.info("post integrit uuid:%s, mac:%s, %s" % (UUID,MacAddress, response.text))
        print("Fail.")
        return False

def send_tick_data(MacAddress, Value):
    global UUID, Now_Mode
    Now_Mode = _Ex
    checkMode()
    current_date = datetime.datetime.now()
    formatted_time = current_date.strftime("%Y-%m-%d %H:%M:%S")
    
    url = "http://svcrg.gb-on.co.kr/raingauge/rgsend"
    
    data = {
        'equipUuid' : UUID,
        'rainGauge' : Value,
        'rainGaugeSendDate': formatted_time
    }
    
    print(data)

    # JSON 데이터를 문자열로 변환
    json_data = json.dumps(data)
    
    # TODO: Try-catch
    # POST 요청 보내기
    response = requests.post(url, data=json_data, headers={'Content-Type': 'application/json'})
    sleep(0.1)
    
    # 응답 확인
    print(response.status_code)
    
    if response.status_code == 200:
        rainLogger.info("post rain value :%s, %s" % (Value, response.text))
        #rainLogger.info(response)
        print("Sent tick data Success.")
        return True
    else:
        rainLogger.info("post rain value :%s, %s" % (Value, response.text))
        print(response)
        print("Fail.")
        return False
        
    rainLogger.info("MACADDRESS")

def send_macaddress():
    
    global UUID,device_MAC, Now_Mode
    Now_Mode = _Ex
    checkMode()
    current_date = datetime.datetime.now()  
    formatted_time = current_date.strftime("%Y-%m-%d %H:%M:%S")
    
    url = "http://svcrg.gb-on.co.kr/raingauge/init"
    data = {
        'startDatetime': formatted_time,
        'macaddress': device_MAC
    }
    
    print(data)
    
    # JSON 데이터를 문자열로 변환
    json_data = json.dumps(data)
    
    # TODO: Try-catch

    response = requests.post(url, data=json_data, headers={'Content-Type': 'application/json'})

    data = response.json()
    print(data)
    if data['data']:
        UUID = data['data']['equipUuid']
        write_uuid(UUID)
    
    # 응답 확인
    if response.status_code == 200:
        rainLogger.info("post regist device mac:%s, %s" % (device_MAC, response.text))
        print("Response is :", response.text)
    else:
        rainLogger.info("post regist device mac:%s, %s" % (device_MAC, response.text))
        print("Fail.")
    return response.text
                
num =1

def check_internet_connection():
    try:
        response = os.system("ping -c 1 google.com > /dev/null 2>&1")
        print(response)
        rainLogger.info("ping")
        return response == 0 
    except urllib.error.URLError:
        return False

def check_server_connection():
    try:
        #urllib.request.urlopen('http://svcrg.gb-on.co.kr/raingauge', timeout=1)
        #사내망 접근시
        #urllib.request.urlopen('http://192.168.1.228:5000/update', timeout=1)
        #외부 접근시
        urllib.request.urlopen('http://222.104.187.58:8756/update', timeout=1)
        return True
    except urllib.error.URLError:
        return False

def delete_old_logs(log_directory):
    # 로그 파일이 있는 디렉토리로 이동
    os.chdir(log_directory)
    print(log_directory)
    # 현재 날짜 가져오기
    current_date = datetime.datetime.now()
    print(current_date)
    # 3일 전 날짜 계산
    three_days_ago = current_date - datetime.timedelta(days=2)
    print("nowTime is : %d before 3day: %d",current_date, three_days_ago)
    
    # 디렉토리 내 모든 파일에 대해 반복
    for filename in os.listdir():
        # 파일인 경우에만 처리
        if os.path.isfile(filename):
            # 파일의 생성 시간 가져오기
            creation_time = datetime.datetime.fromtimestamp(os.path.getctime(filename))
            print("creation_time is :",creation_time)
            # 만약 생성된 지 3일 이상이면 삭제
            if creation_time < three_days_ago:
                os.remove(filename)
                print(f"{filename} 파일이 삭제되었습니다.")
    os.chdir('/home/pi/mu_code/')
        
def checkMode():
        global Now_Mode
        if Now_Mode == _Error :
                print("Error")
                GPIO.output(ledR_Error, True)
                #Before_Mode=Now_Mode
        elif Now_Mode == _Idle :
                print("Idle")
                GPIO.output(ledR_Error, False)
                GPIO.output(ledB_Standby, True)     
        elif Now_Mode == _Ex :
                print("Ex")
                GPIO.output(ledR_Error, False)
                GPIO.output(ledB_Standby, True)          

def get_mac_address(interface='eth0'):
    try:
        # ip 명령을 사용하여 MAC 주소를 얻음
        result = subprocess.check_output(['ip', 'link', 'show', interface])
        # 결과에서 MAC 주소를 파싱
        mac_address = result.decode().split('link/ether ')[1].split(' ')[0]
        print(mac_address)
        return mac_address
    except Exception as e:
        print("MAC 주소를 가져오는 중 오류가 발생했습니다:", e)
        return None

def initialize_info_file(filepath):
    initial_data = {
        "equipUuid": "",
        "version": "1.0.1"
    }
    try:
        with open(filepath, 'w') as file:
            json.dump(initial_data, file)
    except IOError as e:
        print(f"Error: Unable to initialize the file: {e}")

def get_uuid():
    filepath = '/home/pi/mu_code/info.json'
    
    try:
        with open(filepath, 'r') as file:
            content = file.read()
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found. Initializing file.")
        initialize_info_file(filepath)
        return None
    except IOError as e:
        print(f"Error: An I/O error occurred while reading the file: {e}. Initializing file.")
        initialize_info_file(filepath)
        return None

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Error: JSON decoding failed: {e}. Initializing file.")
        initialize_info_file(filepath)
        return None

    if 'equipUuid' not in data:
        print("Error: 'equipUuid' key not found in the JSON data. Initializing file.")
        initialize_info_file(filepath)
        return None

    return data['equipUuid']

def write_uuid(uuid):
    with open('/home/pi/mu_code/info.json', 'r') as file:
        content = file.read()
        data = json.loads(content)   
    with open('/home/pi/mu_code/info.json', 'w') as file:
        data['equipUuid'] = uuid
        print(data)
        data = json.dumps(data)
        result = file.write(data)
        print("result is :", result)

def get_version():
    filepath = '/home/pi/mu_code/info.json'
    
    try:
        with open(filepath, 'r') as file:
            content = file.read()
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found. Initializing file.")
        initialize_info_file(filepath)
        return None
    except IOError as e:
        print(f"Error: An I/O error occurred while reading the file: {e}. Initializing file.")
        initialize_info_file(filepath)
        return None

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Error: JSON decoding failed: {e}. Initializing file.")
        initialize_info_file(filepath)
        return None

    if 'version' not in data:
        print("Error: 'version' key not found in the JSON data. Initializing file.")
        initialize_info_file(filepath)
        return None

    return data['version']

def check_Tick():
    global tick_CNT, Now_Mode
    #new version is GPIO.LOW
    if GPIO.input(rain) == GPIO.LOW:
        sleep(0.05)
        if GPIO.input(rain) == GPIO.LOW:
            tick_CNT += 1
            Now_Mode = _Ex
            checkMode()
            print(tick_CNT,'Tick')
            rainLogger.info("Ticked")
            sleep(0.5)

def check_midNight():
    
    now = datetime.datetime.now()
    # 자정인지 확인
    if now.hour == 0 and now.minute == 0:
        os.system('sudo reboot')

def check_oneSec():
    global before_Sec
    now = datetime.datetime.now()
    nowSec = now.second
    
    if not before_Sec == nowSec:
        before_Sec = nowSec
        return True
    else:
        return False

def check_oneMinut():
    global before_Min
    now = datetime.datetime.now()
    nowMinute = now.minute
    
    if not before_Min == nowMinute:
        before_Min = nowMinute
        return True
    else:
        return False
    
def check_regist_device():
    global UUID, device_MAC
    if UUID == '':
        # eth0 인터페이스의 MAC 주소 가져오기
        print("라즈베리 파이의 MAC 주소:", device_MAC)
        response = send_macaddress()
        write_uuid(UUID)


def download_file(url, local_filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

def extract_zip(zip_filename, extract_to):
    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def check_for_update(server_url, current_version):
    global UUID, device_MAC
    response = requests.get(f"{server_url}/check_update", params={'version': current_version, 'uuid':UUID,'mac': device_MAC})
    response.raise_for_status()
    print(response)
    return response.json()

def check_ota():
    server_url = 'http://222.104.187.58:8756'
    #server_url = 'http://192.168.1.228:5000'
    current_version = get_version()
    zip_filename = 'test.zip'
    extract_to = ''#'update'

    print(f"Checking for updates (current version: {current_version})...")
    update_info = check_for_update(server_url, current_version)

    if update_info['update_available']:
        print(f"New version {update_info['version']} available, downloading...")   
        download_file(f"{server_url}/update", zip_filename)
        print(f"Extracting {zip_filename} to {extract_to}...")
        extract_zip(zip_filename, extract_to)
        print("Update completed successfully.")  
        os.system('sudo reboot')
    else:
        print("No update available.")


# 함수 안에서 실행하면, 값이 안올라옴
device_MAC = get_mac_address('eth0')

InitSys()

while True:
        
        #자정체크 및 리부트
        check_midNight()

        if not Now_Mode == _Error:
            if check_oneMinut():
                cpu_temp = get_cpu_temperature()
                print("cpu_temp is", round(cpu_temp,1))
                check_Tick()
                if not check_internet_connection():
                    GPIO.output(ledG_Internet, False)
                    Now_Mode = _Error
                else:
                    GPIO.output(ledG_Internet, True)
                    GPIO.output(ledB_Standby, False)
                    check_Tick()
                    Sum = tick_CNT*0.5
                    if not send_tick_data(device_MAC,round(Sum,1)):
                        print('1')
                        if not send_tick_data(device_MAC,round(Sum,1)):
                            print('2')
                            if not send_tick_data(device_MAC,round(Sum,1)):
                                print('3')
                                Now_Mode = _Error
                                continue
                    else:
                        print('0')
                tick_CNT=0
                checkMode()
        else:
            GPIO.output(ledG_Internet, False)
            GPIO.output(ledB_Standby, False)
            
            if not check_internet_connection():
                GPIO.output(ledG_Internet, False)
            else:
                GPIO.output(ledG_Internet, True)
                Now_Mode = _Idle
                checkMode()
            
            if check_oneSec():
                if not check_internet_connection():
                    GPIO.output(ledG_Internet, False)
                else:
                    GPIO.output(ledG_Internet, True)
                    Now_Mode = _Idle
                
                output_state = GPIO.input(ledR_Error)
                if output_state == GPIO.LOW:
                    GPIO.output(ledR_Error, True)
                else:
                    GPIO.output(ledR_Error, False)
            
            if check_oneMinut():
                check_Tick()
                Sum = tick_CNT*0.5
                rainLogger.info(Sum)
                print('Saved in log :', Sum)
                tick_CNT=0
        
        CNT_num += 1
        check_Tick()
            

 
            
            
                
        
        
