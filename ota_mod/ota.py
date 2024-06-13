#import network
import requests
import os
import json
#import machine
from time import sleep


class OTAUpdater:
    """ This class handles OTA updates. It connects to the Wi-Fi, checks for updates, downloads and installs them."""
    def __init__(self, ssid, password, repo_url, filename):
        self.filename = filename
        self.ssid = ssid
        self.password = password
        self.repo_url = repo_url
        self.ver_url = repo_url + 'version.json'
        
        # get the current version (stored in version.json)
        if 'version.json' in os.listdir():    
            with open('version.json') as f:
                self.current_version = json.load(f)['version']
            print(f"Current device firmware version is '{self.current_version}'")

        else:
            self.current_version = "0"
            # save the current version
            with open('version.json', 'w') as f:
                json.dump({'version': self.current_version}, f)
    
    def connect_wifi(self):
        """ Connect to Wi-Fi."""
        sta_if = network.WLAN(network.STA_IF)
        sta_if.active(True)
        sta_if.connect(self.ssid, self.password)
        cnt=0
        while not sta_if.isconnected():
            if cnt>50:
                return False
            print('.', end="")
            sleep(0.25)
            cnt = cnt+1
        print(f'Connected to WiFi, IP is: {sta_if.ifconfig()[0]}')
        return True

    def Disconnect_wifi(self):
        """ Disconnect to Wi-Fi."""
        sta_if = network.WLAN(network.STA_IF)
        sta_if.active(False)
        
    def check_for_updates(self):
        """ Check if updates are available."""
        # Connect to Wi-Fi
        #self.Disconnect_wifi()
        #if not self.connect_wifi():
        #    return False     
        print('Checking for latest version...')
        try:
            response = requests.get(self.ver_url)
        except Exception as e:
            print('Error during HTTP request:', e)
        print(response.status_code)
        data = json.loads(response.text)
        self.latest_version = next(iter(data.values()))
        
        print(f'latest version is: {self.latest_version}')
        # compare versions
        newer_version_available = True if self.current_version != self.latest_version else False
        print(f'Newer version available: {newer_version_available}')
        return newer_version_available
    
    def download_and_install_update_if_available(self):
        """ Check for updates, download and install them."""
        if self.check_for_updates():
            if self.fetch_latest_code():
                self.update_no_reset()
                self.update_and_reset()
        else:
            print('No new updates available.')
            
    def download_and_install_update_if_available_for_ugit(self):
        """ Check for updates, download and install them."""
        if self.check_for_updates():
            self.save_new_version()
            return True
        else:
            print('No new updates available.')
            return False

    #added by JS 240103
    def save_new_version(self):
        # update the version in memory
        self.current_version = self.latest_version
        # save the current version
        with open('version.json', 'w') as f:
            json.dump({'version': self.current_version}, f)
