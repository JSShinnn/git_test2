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

from logging import handlers
import logging

import serial
import re

import urllib.request

import subprocess



#Log 설정
####################################################################################################################################
# Ensure the directory exists
log_directory = "/home/pi/mu_code/log"

log_directory = os.path.join(log_directory)

if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Update the filename to include the log directory
filename = os.path.join(log_directory, 'rain.log')

#log settings
rainLogFormatter = logging.Formatter('%(asctime)s,%(message)s')

#handler settings
rainLogHandler = handlers.TimedRotatingFileHandler(filename=filename, when='midnight', interval=1, encoding='utf-8')
rainLogHandler.setFormatter(rainLogFormatter)
rainLogHandler.suffix = "%Y%m%d"

#logger set
rainLogger = logging.getLogger()
rainLogger.setLevel(logging.INFO)
rainLogger.addHandler(rainLogHandler)

####################################################################################################################################
#mode_state
# 0 = Initing
# 1 = only Internet
# 2 = only GPS
# 3 = Internet + GPS
# 4 = Error

Mode_state = (0,0,0,0,0,0)

#강수량 측정
rain = 15

#LED관련
ledG_Internet = 27
ledR_Error = 26
ledB_Ex = 13
ledG_Standby= 25

tick_CNT=0
CNT_num=0

UUID =''

#GPIO
GPIO.setmode(GPIO.BCM)

#rain 게이지
GPIO.setup(rain, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#set LED
GPIO.setup(ledG_Standby, GPIO.OUT)
GPIO.setup(ledG_Internet, GPIO.OUT)
GPIO.setup(ledR_Error, GPIO.OUT)
GPIO.setup(ledB_Ex, GPIO.OUT)

before_Sec=0
before_Min=0
#Before_Mode = 0
Now_Mode = ''
device_MAC = ''

_Init = ('init',)
_Idle = ('idle',)
_Ex = ('Ex')
_Error = ('Error')


def InitSys():
        global log_directory, before_Min, UUID, device_MAC
        print("Init Sys....")
        Mode_state = _Init
        GPIO.output(ledG_Internet, True)   
        GPIO.output(ledR_Error, True)   
        GPIO.output(ledG_Standby, True)
        
        #led 초기화
        GPIO.output(ledG_Internet, False)   
        GPIO.output(ledR_Error, False)

        if not check_internet_connection():
            GPIO.output(ledG_Internet, False)
        else:
            GPIO.output(ledG_Internet, True)
            
        Now_Mode = "Idle"
        checkMode()
        print("Finished Init Sys!!")
        delete_old_logs(log_directory)
        
        now = datetime.datetime.now()
        before_Min = now.minute
               
        #UUID 가져오기
        UUID = get_uuid()
        print(UUID)
        
        check_regist_device()
        
        #MAC 가져오기
        get_mac_address('eth0')
        # temp_MAC = get_mac_address('eth0')
        # send_macaddress(temp_MAC)

def send_restart(MacAddress):
    global UUID
    Now_Mode = _Ex
    checkMode()
    current_date = datetime.now()
    formatted_time = current_date.strftime("%Y-%m-%d %H:%M:%S")
    url = "http://devrg.gb-on.co.kr/raingauge/reboot"
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
        rainLogger.info("success restart")
        print("Response is :", response.text)
        #os.system('sudo reboot')
    else:
        print(response)
        print("Fail.")
    return response.text

def send_tick_data(MacAddress, Value):
    global UUID
    Now_Mode = _Ex
    checkMode()
    current_date = datetime.datetime.now()
    formatted_time = current_date.strftime("%Y-%m-%d %H:%M:%S")
    
    url = "http://devrg.gb-on.co.kr/raingauge/rgsend"
    
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

    # 응답 확인
    print(response.status_code)
    if response.status_code == 200:
        rainLogger.info("Sent tick to web")
        print("Sent tick data Success.")
        return True
    else:
        print(response)
        print("Fail.")
        return False
        
    rainLogger.info("MACADDRESS")

def send_macaddress():
    
    global UUID,device_MAC
    Now_Mode = _Ex
    checkMode()
    current_date = datetime.datetime.now()  
    formatted_time = current_date.strftime("%Y-%m-%d %H:%M:%S")
    
    url = "http://devrg.gb-on.co.kr/raingauge/init"
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
    UUID = data['data']['equipUuid']
    
    # 응답 확인
    if response.status_code == 200:
        rainLogger.info("sucess registed")
        print("Response is :", response.text)
    else:
        print(response)
        print("Fail.")
    return response.text

# def checkInternet():
#         ipaddress=socket.gethostbyname(socket.gethostname())
#         if ipaddress=="127.0.0.1:5010/api/v1/collect_api/save_collect_data/":
#                 print("internet-off")
#                 GPIO.output(ledG_Internet, False)    
#         else:
#                 # print("internet-on")
#                 GPIO.output(ledG_Internet, True)
                

def check_internet_connection():
    try:
        #urllib.request.urlopen('http://devrg.gb-on.co.kr/raingauge', timeout=1)
        urllib.request.urlopen('https://www.google.com', timeout=1)
        return True
    except urllib.error.URLError:
        return False

def delete_old_logs(log_directory):
    # 로그 파일이 있는 디렉토리로 이동
    os.chdir(log_directory)
    print(log_directory)
    # 현재 날짜 가져오기
    current_date = datetime.datetime.now()
    
    # 3일 전 날짜 계산
    three_days_ago = current_date - datetime.timedelta(days=3)
    print(three_days_ago)
    
    # 디렉토리 내 모든 파일에 대해 반복
    for filename in os.listdir():
        # 파일인 경우에만 처리
        if os.path.isfile(filename):
            # 파일의 생성 시간 가져오기
            creation_time = datetime.datetime.fromtimestamp(os.path.getctime(filename))
            # 만약 생성된 지 3일 이상이면 삭제
            if creation_time > three_days_ago:
                os.remove(filename)
                print(f"{filename} 파일이 삭제되었습니다.")
        
def checkMode():
        #Now_Mode = _Error
        #if Now_Mode == Before_Mode :
        #        return
        Mode=''
        if Now_Mode == _Error :
                print("Error")
                GPIO.output(ledR_Error, True)
                #Before_Mode=Now_Mode
        elif Now_Mode == _Idle :
                #print("Idle")
                GPIO.output(ledG_Standby, True)     
        elif Now_Mode == _Ex :
                print("Ex")
                GPIO.output(ledG_Standby, True)          

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

def get_uuid():
    with open('/home/pi/mu_code/uuid.json', 'r') as file:
        # 파일 내용 읽기
        content = file.read()
    data = json.loads(content)
    return data['equipUuid']

def write_uuid(uuid):
    with open('/home/pi/mu_code/uuid.json', 'w') as file:
        json.dump({'equipUuid': uuid }, file)

def check_Tick():
    global tick_CNT
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

#send_restart(device_MAC)

# 함수 안에서 실행하면, 값이 안올라옴
device_MAC = get_mac_address('eth0')

InitSys()

while True:
        # if not check_internet_connection():
        #     sleep(0.1)
        #     if not check_internet_connection():
        #         sleep(0.1)
        #         if not check_internet_connection():
        #             Now_Mode = _Error
        #             checkMode()
        #             GPIO.output(ledG_Internet, False)
        #             GPIO.output(ledR_Error, True)
        # else:
        #     # 프로그램 종료
        #     #subprocess.run(['killall', 'python3.9', 'test.py'])
        #     # 프로그램 재실행
        #     #subprocess.run(['python3', 'test.py'])
        #     #subprocess.run(['sudo', 'reboot'])
        #     GPIO.output(ledG_Internet, True)
        #     GPIO.output(ledR_Error, False)
        # #GPIO.output(ledR_Error, True)
        # GPIO.output(ledG_Standby, False)
        # GPIO.output(ledB_Ex, True)
        #Now_Mode = _Error
        
        check_midNight()
        
        if not Now_Mode == _Error:
            #자정체크 및 리부트
            
            if check_oneMinut():
                check_Tick()
                if not check_internet_connection():
                    GPIO.output(ledG_Internet, False)
                else:
                    GPIO.output(ledG_Internet, True)
                check_Tick()
                Sum = tick_CNT*0.5
                if send_tick_data(device_MAC,round(Sum,1)):
                    if send_tick_data(device_MAC,round(Sum,1)):
                        if send_tick_data(device_MAC,round(Sum,1)):
                            Now_Mode = _Error
                            continue
                tick_CNT=0
                Now_Mode = _Idle
                checkMode()
        else:
            GPIO.output(ledG_Internet, False)
            GPIO.output(ledG_Standby, False)
            
            if check_oneSec():
                output_state = GPIO.input(ledR_Error)
                if output_state == GPIO.HIGH:
                    GPIO.output(ledR_Error, False)
                else:
                    GPIO.output(ledR_Error, True)
            
            if check_oneMinut():
                check_Tick()
                Sum = tick_CNT*0.5
                rainLogger.info(Sum)
                print('Saved in log :', Sum)
                tick_CNT=0
        
        CNT_num += 1
        check_Tick()
            

 
            
            
                
        
        
