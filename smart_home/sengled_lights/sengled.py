"""
Parse Plex Media Server statistics via Tautulli's API
Copyright (C) 2019 Nathan Harris
"""

import discord
from discord.ext import commands, tasks
from discord.utils import get
import json
import requests
import os
import asyncio

creds = {}
with open('smart_home/sengled_lights/config.txt', 'r') as f:
    creds = eval(f.read())
f.close()

base_url = 'https://us-elements.cloud.sengled.com:443/zigbee'

class Sengled(commands.Cog):
    
    logged_in = False
    
    devices = {}
    
    headers = {'Content-Type': 'application/json',
                'Cookie': 'JSESSIONID={}'.format(creds['session_id'])
    }
    
    def login(self):
        if self.logged_in:
            return
        data = {
            'uuid': 'xxx',
            'isRemote': 'true',
            'user': creds['username'],
            'pwd': creds['password'],
            'os_type': 'android'
        }
        try:
            r = requests.post(base_url + '/customer/remoteLogin.json', headers=self.headers, json=data)
            resp_json = json.loads(r.text)
            if not creds['session_id']:
                self.headers['Cookie'] = 'JSESSIONID={}'.format(resp_json['jsessionid'])
                creds['session_id'] = resp_json['jsessionid']
                self.saveCreds()
            self.logged_in = True
            return resp_json
        except Exception as e:
            print(e)
            return None
        
    def saveCreds(self):
        with open('smart_home/sengled_lights/config.txt', 'w') as f:
            f.write(str(creds))
        f.close()
        
    def getDevices(self):
        try:
            r = requests.post(base_url + '/room/getUserRoomsDetail.json', headers=self.headers, json={})
            deviceList = []
            for room in json.loads(r.text)['roomList']:
                for device in room['deviceList']:
                    deviceList.append({
                        'room': room['roomName'],
                        'name': device['deviceName'],
                        'uuid': device['deviceUuid'],
                        'status': ('on' if device['onoff'] == 1 else 'off'),
                        'brightness': device['brightness']
                    })
            return deviceList
        except Exception as e:
            print(e)
            return None
        
    def getDevice(self, deviceID):
        for d in self.devices:
            if d['Uuid'] == deviceID:
                return d
        return None
        
    def getDeviceId(self, name):
        for d in self.devices:
            if d['name'].lower() == name.lower():
                return d['uuid']
        return None
    
    def getDeviceNames(self):
        names = []
        for d in self.devices:
            names.append(d['name'])
        return names
    
    def update(self):
        try:
            if self.login():
                self.devices = self.getDevices()
                if self.devices != None:
                    return True
        except Exception as e:
            print(e)
        return False
    
    def setLight(self, deviceID, newState):
        try:
            data = {
                'deviceUuid': deviceID,
                'onoff': (0 if newState.lower() == 'off' else 1)
            }
            r = requests.post(base_url + '/device/deviceSetOnOff.json', headers=self.headers, data=data)
            if r.status_code == 200 and self.changeState(deviceID, 'status', newState.lower()):
                return newState
            else:
                return None
        except Exception as e:
            print(e)
            return None
        
    def setBrightness(self, deviceID, newBrightness):
        try:
            # convert 0-100 to 0-255
            value = (newBrightness / 100) * 255
            data = {
                'deviceUuid': deviceID,
                'brightness': str(value)
            }
            r = requests.post(base_url + '/device/deviceSetBrightness.json', headers=self.headers, data=data)
            if r.status_code == 200:
                return True
            else:
                return False
        except Exception as e:
            print(e)
            return None
        
    def changeState(self, deviceID, key, value):
        for d in self.devices:
            if d['deviceUuid'] == deviceID:
                d[key] = value
                return True
        return False
        
    @commands.command(name="lights", aliases=["light"], pass_context=True)
    async def sengled(self, ctx: commands.Context, *, command: str):
        """
        Control Sengled lights
        """
        commands = command.split(" ")
        if len(commands) > 1: # assume "[device] [command]"
            device = self.getDeviceId(commands[0])
            if device != None:
                if commands[1].lower() in ['on','off']: # if command is 'on' or 'off'
                    self.setLight(device, commands[1].lower())
                if commands[1].isnumeric() and int(commands[1]) <= 100 and int(commands[1]) >= 0:
                    self.setBrightness(device, int(commands[1]))
                else:
                    await ctx.send("Invalid command.")
            else:
                await ctx.send("That device doesn't exist.")
        else:
            if command == 'list':
                response = ""
                for d in self.getDevices():
                    response += "{name} - {room}\n".format(name=d['name'], room=d['room'])
                if response:
                    await ctx.send(response[:-1])
                else:
                    await ctx.send("No devices found.")
            elif command in self.getDeviceNames(): # if command is just device name, assume toggle state
                id = self.getDeviceId(command)
                state = self.getDevice(id)['status']
                if state == 'on':
                    state = 'off'
                else:
                    state = 'on'
                self.setLight(id, state)
            else:
                await ctx.send("Invalid command.")
    
    def __init__(self, bot):
        self.bot = bot
        if self.update():
            print("Sengled ready to go.")
