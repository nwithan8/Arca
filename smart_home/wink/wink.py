"""
Interact with Wink Hubs and connected devices
Copyright (C) 2019 Nathan Harris
"""

import discord
from discord.ext import commands, tasks
from discord.utils import get
import json
import requests
import os
import asyncio
import pywink

creds_folder = "smart_home/wink/"
creds = {}
with open(creds_folder + 'config.json', 'r') as f:
    creds = eval(f.read())
f.close()

class Wink(commands.Cog):
    
    def setup(self):
        if "access_token" not in creds.keys():
            print("Visit the following page to sign in:\n" + pywink.get_authorization_url(creds['client_id'], creds['redirect_uri']))
            code = input("Enter code from URL:")
            auth = pywink.request_token(code, creds['client_secret'])
            pywink.set_wink_credentials(creds['client_id'], creds['client_secret'], auth.get("access_token"), auth.get("refresh_token"))
                
            file_contents = {
                'client_id': creds['client_id'],
                'client_secret': creds['client_secret'],
                'redirect_uri': creds['redirect_uri'],
                'access_token': auth.get('access_token'),
                'refresh_token': auth.get('refresh_token')
            }
            f = open(creds_folder + 'config.json', 'w+')
            f.write(json.dumps(file_contents))
            f.close()
    
    def authenticate(self):
        global creds
        if creds['access_token']:
            pywink.set_wink_credentials(creds['client_id'], creds['client_secret'], creds['access_token'], creds['refresh_token'])
        else:
            print("Visit the following page to sign in:\n" + pywink.get_authorization_url(creds['client_id'], creds['redirect_uri']))
            code = input("Enter code from URL:")
            auth = pywink.request_token(code, creds['client_secret'])
            pywink.set_wink_credentials(creds['client_id'], creds['client_secret'], auth.get("access_token"), auth.get("refresh_token"))
            creds['access_token'] = auth.get('access_token')
            creds['refresh_token'] = auth.get('refresh_token')
            self.saveCreds()
            
    def saveCreds(self):
        f = open(creds_folder + 'config.json', 'w+')
        f.write(json.dumps(creds))
        f.close()
    
    def getDevice(self, name):
        devices = pywink.get_all_devices()
        for d in devices:
            if d.name().lower() == name.lower():
                return d, d.object_type()
        return None, None
    
    def getGroup(self, name):
        groups = pywink.get_light_groups()
        for g in groups:
            if g.name().lower() == name.lower():
                return g, g.object_type()
        return None, None
    
    def getDeviceOrGroup(self, name):
        device, device_type = self.getDevice(name)
        if not device:
            device, device_type = self.getGroup(name)
        return device, device_type
        
    def getDeviceNames(self):
        devices = pywink.get_all_devices()
        names = []
        for d in devices:
            names.append(d.name())
        return names
    
    def findDeviceOrGroup(self, name):
        device, device_type = self.getDeviceOrGroup(name)
        if not device:
            name = self.findNameWithNick(name)
            if name:    
                device, device_type = self.getDeviceOrGroup(name)
        return device, device_type
    
    def listLights(self):
        r = ""
        lights = pywink.get_light_bulbs()
        for l in lights:
            r += ("```css\n" if l.state() else "```brainfuck\n") + l.name() + " - " + ("ON" if l.state() else "OFF") +("\n```")
        return r
    
    def listGroups(self):
        r = ""
        groups = pywink.get_light_groups()
        for g in groups:
            r += '{color}{name} ({type}) - {state}\n```'.format(color=("```css\n" if g.state() else "```brainfuck\n"), name=g.name(),type='lights',state=("ON" if g.state() else "OFF"))
        groups = pywink.get_binary_switch_groups()
        for g in groups:
            r += '{color}{name} ({type}) - {state}\n```'.format(color=("```css\n" if g.state() else "```brainfuck\n"), name=g.name(),type='switches',state=("ON" if g.state() else "OFF"))
        groups = pywink.get_shade_groups()
        for g in groups:
            r += '{color}{name} ({type}) - {state}\n```'.format(color=("```css\n" if g.state() else "```brainfuck\n"), name=g.name(),type='shades',state=("ON" if g.state() else "OFF"))
        return r
    
    def listDevices(self):
        r = ""
        devices = pywink.get_all_devices()
        for d in devices:
            r += '{color}{name} ({type}) - {state}\n```'.format(color=("```css\n" if d.state() else "```brainfuck\n"),name=d.name(),type=d.object_type(),state=("ON" if d.state() else "OFF"))
        return r
            
    def setNickname(self, command):
        commands = command.split()
        name = ' '.join(commands[1:-1])
        nickname = str(commands[-1]) # nickname can only be one word
        device, device_type = self.getDevice(name)
        if not device:
            name = self.findNameWithNick(name)
            if name:    
                device, device_type = self.getDevice(name)
        if device:
            if device.name().lower() in creds.keys():
                creds[device.name().lower()].append(nickname)
            else:
                creds[device.name().lower()] = [nickname]
            self.saveCreds()
            return True
        else:
            return False
            
    def findNameWithNick(self, nick):
        for k,v in creds.items():
            if nick in v:
                return k
        return None
    
    @commands.command(name="wink", pass_context=True)
    async def wink(self, ctx: commands.Context, *, commands: str = None):
        """
        Wink (smart home) commands
        """
        if commands:
            commands = commands.split()
            control = False
            device = None
            device_type = None
            if commands[-1].isnumeric(): # ended with number, so controlling brightness on bulb
                name = ' '.join(commands[0:-1])
                device, device_type = self.findDeviceOrGroup(name)
                control = True
            else:
                name = ' '.join(commands)
                device, device_type = self.findDeviceOrGroup(name)
            if device:
                if device_type == 'light_bulb':
                    if control:
                        device.set_state(device.state(), brightness=float(commands[-1])/100)
                    else:
                        device.set_state(not device.state())
                device.update_state()
            else:
                command = ' '.join(commands)
                if command in ['list','device','devices']:
                    r = self.listDevices()
                    if r:
                        await ctx.send(r)
                elif command in ['lights','bulbs']:
                    r = self.listLights()
                    if r:
                        await ctx.send(r)
                elif command in ['group','groups']:
                    r = self.listGroups()
                    if r:
                        await ctx.send(r)
                elif 'nick' in command:
                    if self.setNickname(command):
                        await ctx.send("Nickname saved.")
                    else:
                        await ctx.send("Nickname could not be saved.")
                else:    
                    await ctx.send("I couldn't find that device.")
        else:
            await ctx.send("What command?")
    
    @commands.command(name="color", pass_context=True)
    async def color(self, ctx: commands.Context, colorType: str, value: int, *, deviceName: str):
        """
        Set a color for a light bulb
        colorType: "hue" for hue, "sat" for saturation, "temp" for temperature
        """
        await ctx.send("Hello.")
    
    def __init__(self, bot):
        self.bot = bot
        self.setup()
        self.authenticate()
        print("Wink ready to go.")


def setup(bot):
    bot.add_cog(Wink(bot))