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
import time
import pychromecast as pc
from gtts import gTTS
from googlehomepush import GoogleHome
from tempfile import TemporaryFile
import socket

audio_file_dir = "/var/www/html/home_audio"

class GoogleHome(commands.Cog):
    
    cast = None
    ip = None
    
    def setup(self, name):
        chromecasts = pc.get_chromecasts()
        for cc in chromecasts:
            print(cc.device.friendly_name)
            if cc.device.friendly_name == name:
                cc.wait()
                self.cast = cc
                break
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        self.ip = s.getsockname()[0]
        s.close()
            
    def play_tts(self, text, lang='en', slow=False):
        tts = gTTS(text=text, lang=lang, slow=slow)
        #f = TemporaryFile()
        #tts.write_to_fp(f)
        with open(audio_file_dir + '/test.mp3', 'wb') as f:
            tts.write_to_fp(f)
            self.cast.wait()
            mc = self.cast.media_controller.play_media('http://"{ip}""{path}"/test.mp3'.format(
                ip=self.ip,
                path=audio_file_dir
                ), 'audio/mp3')
            mc.block_until_active()
            f.close()
        
    def speak(self, name, text, lang='en-US'):
        GoogleHome(name).say(text, lang)
    
    @commands.command(name="speak", pass_context=True)
    async def google_home_say(self, ctx: commands.Context, *, text: str):
        """
        Speak through Google Home
        """
        self.play_tts(text)
    
    def __init__(self, bot):
        self.bot = bot
        self.setup('Bedroom speaker')
        #self.speak('Bedroom speaker', 'Hello')
        print("Google Home ready to go.")
