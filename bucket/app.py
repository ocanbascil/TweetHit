#!/usr/bin/env python

import time
from getpass import getpass
from textwrap import TextWrapper
import logging
import tweepy
import tweepy_bucket
from tweepy.api import API
from tweepy_bucket.models import SimpleStatus
from tweepy_bucket.stream import BucketListener



def main():
    # Prompt for login credentials and setup stream object
    username = ''
    password = ''
    stream = tweepy.Stream(username, password, 
                    BucketListener(ban_list_path = 'banned_users.txt'),
                    timeout=None)


    track_list = 'amazon,amzn,asin,isbn,book http,game http,deal http,livre http,jeu http,dvd http,spiel http,buch http,faire http'
    track_list = [k for k in track_list.split(',')]
    
    
    try:
        start_time = time.time()
        while True:
            
            if not stream.running:
                print 'Connection closed, trying to restart'
                stream.filter(None, track_list,async = True)
            else:
                print 'Connection alive'
            
            
            time.sleep(10)
            now = time.time()   
            print 'Timer: %s' % (now - start_time)        
            
            if now - start_time > 3600:
                print '1 hour complete, restarting connection'
                start_time = time.time()
                stream.disconnect()
                print 'Stream status: ',stream.running
                

                
            
                
    except KeyboardInterrupt:
        print 'Disconnecting stream'
        stream.disconnect()

if __name__ == '__main__':
    main()