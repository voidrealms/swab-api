  
"""
Based on Alex's client
https://github.com/alexgolec/schwab-py/blob/main/schwab/auth.py
"""

import logging
import urllib
import json
from datetime import datetime, timezone
import os
from authlib.integrations.httpx_client import AsyncOAuth2Client, OAuth2Client

class Client:
    def __init__(self) -> None:
        self.filepath = 'swab-token.json'
        self.api_key = 'KEY-HERE'
        self.app_secret = 'SECRET-HERE'
        self.callback_url = 'https://127.0.0.1'
        self.TOKEN_ENDPOINT = 'https://api.schwabapi.com/v1/oauth/token'
        self.session:OAuth2Client = None

    def setup(self):
        try:
            oauth = OAuth2Client(self.api_key, redirect_uri=self.callback_url)
            authorization_url, state = oauth.create_authorization_url('https://api.schwabapi.com/v1/oauth/authorize')

            print('Click the link below')
            print(authorization_url)

            redirected_url = input('Paste URL:').strip()
            token = oauth.fetch_token(self.TOKEN_ENDPOINT,authorization_response=redirected_url,client_id=self.api_key, auth=(self.api_key, self.app_secret))
            self.write_token(token)
            self.check_session()

        except Exception as e:
            logging.error('Setup failed!')
            logging.exception(e)
            return False
        
    def check_session(self) -> bool:
        try:
            logging.debug('Checking session')
            if(self.session is None):
                self.session = self.load_session()
            if(self.session is None):
                raise Exception('Session could not be loaded, please run setup!')
       
            format = '%Y-%m-%d %H:%M:%S'
            expires = datetime.fromtimestamp(int(self.session.token['expires_at']),timezone.utc)
            current = datetime.now(timezone.utc)
            td = (expires - current)
            minutes = td.total_seconds() / 60

            logging.debug('Expires: {expires}'.format(expires=expires.strftime(format)))
            logging.debug('Current: {current}'.format(current=current.strftime(format)))
            logging.debug('Minutes: {minutes}'.format(minutes=minutes))
            if(minutes <=0):
                self.refesh_token()
       
        except Exception as e:
            logging.error('Checking session failed!')
            logging.exception(e)
            return False

    def read_token(self) -> dict | None:
        try:
            logging.debug('Reading token')
            if(os.path.exists(self.filepath) == False):
                raise FileNotFoundError(self.filepath)
            with open(self.filepath,'r') as f:
                token = json.load(f)
            return token
        except Exception as e:
            logging.error('Token could not be loaded')
            logging.exception(e)
            return None
    
    def write_token(self,token,*args,**kwargs):
        try:
            logging.debug('Writing token')
            with open(self.filepath,'w') as f:
                json.dump(token,f)
            self.session = self.load_session()
        except Exception as e:
            logging.error('Token could not be loaded')
            logging.exception(e)

    def refesh_token(self):
        try:
            #refresh token = 90 days
            #access_token = 30 minutes
            logging.debug('Refreshing token')
            if(self.session is None):
                self.session = self.load_session()
            if(self.session is None):
                raise Exception('Session not loaded!')
            token = self.read_token()
            new_token = self.session.fetch_token(self.TOKEN_ENDPOINT,grant_type='refresh_token',refresh_token=token['refresh_token'],access_type='offline')
            assert(new_token != token)
            self.write_token(new_token)
            
            print('Token refreshed')
        except Exception as e:
            logging.error('Token could not be loaded')
            logging.exception(e)

    def load_session(self) -> OAuth2Client | None:
        try:
            logging.debug('Loading session')
            token = self.read_token()
            return OAuth2Client(self.api_key,client_secret=self.app_secret,token=token,token_endpoint=self.TOKEN_ENDPOINT,update_token=self.write_token)
        except Exception as e:
            logging.error('Could not load session')
            logging.exception(e)
            return None
    
    def clean_symbol(self,symbol:str) -> str:
        return symbol.replace('.X','')

    def get_Qoute(self,underlying) -> dict:
        try:
            if(self.check_session() == False):
                raise Exception('No valid session')
            underlying = self.clean_symbol(underlying)
            logging.debug('Getting qoute for: {underlying}'.format(underlying=underlying))
            endpoint = 'https://api.schwabapi.com/marketdata/v1/{underlying}/quotes'.format(underlying=underlying)
            response = self.session.get(endpoint)
            return json.loads(response.text)
        except Exception as e:
            logging.error('Could not get qoute for {underlying}'.format(underlying=underlying))
            logging.exception(e)
            return None

    def get_Option(self, underlying:str,expiration:datetime) -> dict:
        try:
            if(self.check_session() == False):
                raise Exception('No valid session')
            underlying = self.clean_symbol(underlying)
            format = '%Y-%m-%d'
            logging.debug('Getting options chain for: {underlying} on {expiration}'.format(underlying=underlying,expiration=expiration.strftime(format)))
            endpoint = 'https://api.schwabapi.com/marketdata/v1/chains'
            params = dict()
            params['symbol'] = underlying
            params['contractType'] = 'ALL'
            params['fromDate'] = expiration.strftime('%Y-%m-%d')
            params['toDate'] = expiration.strftime('%Y-%m-%d')
            response = self.session.get(endpoint,params=params)
            return json.loads(response.text)
        except Exception as e:
            logging.error('Could not get options chain for {underlying}'.format(underlying=underlying))
            logging.exception(e)
            return None
        
if(__name__ == '__main__'):
    logging.basicConfig(format='%(levelname)s - %(asctime)s: %(message)s',datefmt='%H:%M:%S', level=logging.DEBUG)
    client = Client()
    #client.setup() 
    #client.refesh_token()
    #client.check_session()
    qoute = client.get_Qoute('$SPX.X')
    chain = client.get_Option('$SPX.X',datetime.now())

    with open('spx_qoute.json', 'w') as f:
        json.dump(qoute,f)
    with open('spx_chain.json', 'w') as f:
        json.dump(chain,f)
