  
"""
https://github.com/alexgolec/schwab-py/blob/main/schwab/auth.py

"""
import logging
import json
from datetime import datetime, timezone
import os
from authlib.integrations.httpx_client import AsyncOAuth2Client, OAuth2Client

class Client:
    def __init__(self) -> None:
        self.filepath = 'swab_client.json'
        self.TOKEN_ENDPOINT = 'https://api.schwabapi.com/v1/oauth/token'
        self.session:OAuth2Client = None
        self.config = dict()
        self.config['client'] = dict()
        self.config['token'] = dict()

        self.load()

    def setup(self) -> bool:
        try:
            if(os.path.exists(self.filepath)):
                logging.debug('Local configuration found, loading config')
                with open(self.filepath,'r') as f:
                    self.load()
            else:
                logging.debug('Local configuration not found, starting setup')
                self.config['client']['api_key'] = input('API Key:')
                self.config['client']['app_secret'] = input('App Secret:')
                self.config['client']['callback'] ='https://127.0.0.1'
                self.config['client']['setup'] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                self.config['token'] = None

            oauth = OAuth2Client(self.config['client']['api_key'], redirect_uri=self.config['client']['callback'])
            authorization_url, state = oauth.create_authorization_url('https://api.schwabapi.com/v1/oauth/authorize')

            print('Click the link below')
            print(authorization_url)

            redirected_url = input('Paste URL:').strip()
            self.config['token'] = oauth.fetch_token(self.TOKEN_ENDPOINT,authorization_response=redirected_url,client_id=self.config['client']['api_key'], auth=(self.config['client']['api_key'], self.config['client']['app_secret']))
            self.save()
            self.load_session()
            return True
        except Exception as e:
            logging.error('Setup failed!')
            logging.exception(e)
            return False

    def get_Clock(self) -> dict:
        try:
            if(not self.check_session()):
                raise Exception('No valid session')

            format = '%Y-%m-%d'
            expiration = datetime.now(timezone.utc)
            logging.debug('Getting market hours for {expiration}'.format(expiration=expiration.strftime(format)))
            endpoint = 'https://api.schwabapi.com/marketdata/v1/markets'
            params = dict()
            params['markets'] = 'equity'
            params['date'] = expiration.strftime('%Y-%m-%d')

            response = self.session.get(endpoint,params=params)
            return json.loads(response.text)
        except Exception as e:
            logging.error('Could not get market hours!')
            logging.exception(e)
            return None

    def get_Qoute(self,underlying) -> dict:
        try:
            if(not self.check_session()):
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
            if(not self.check_session()):
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
        
    def check_session(self) -> bool:
        try:
            logging.debug('Checking session')
            if(self.session is None):
                self.load_session()

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
            return True
        except Exception as e:
            logging.error('Checking session failed!')
            logging.exception(e)
            return False

    def write_token(self,token,*args,**kwargs):
        try:
            logging.debug('Writing token')
            if('refresh_token' not in token):
                logging.warning('refresh_token not in token from server!')
            self.config['token'] = token
            self.save()
            self.load_session()
        except Exception as e:
            logging.error('Token could not be loaded')
            logging.exception(e)

    def save(self):
        try:
            logging.debug('Saving config')
            with open(self.filepath,'w') as f:
                json.dump(self.config,f)
        except Exception as e:
            logging.error('Token could not be loaded')
            logging.exception(e)

    def load(self):
        try:
            if(os.path.exists(self.filepath) == False):
                logging.warning('Config file not found, run setup!')
                return
            logging.debug('Loading config')
            with open(self.filepath,'r') as f:
                self.config = json.load(f)
        except Exception as e:
            logging.error('Token could not be loaded')
            logging.exception(e)

    def refesh_token(self):
        try:
            #refresh token = 90 days
            #access_token = 30 minutes
            logging.debug('Refreshing token')
            if(self.session is None):
                self.load_session()

            token = self.config['token']
            new_token = self.session.fetch_token(self.TOKEN_ENDPOINT,grant_type='refresh_token',refresh_token=token['refresh_token'],access_type='offline')
            assert(new_token != token)
            self.config['token'] = new_token
            self.save()
            
            print('Token refreshed')
        except Exception as e:
            logging.error('Token could not be loaded')
            logging.exception(e)

    def load_session(self):
        try:
            logging.debug('Loading session')
            if('client' not in self.config):
                self.load()
                if('client' not in self.config):
                    raise Exception('Configuration not set')
            token = self.config['token']
            self.session = OAuth2Client(self.config['client']['api_key'],self.config['client']['app_secret'],token=token,token_endpoint=self.TOKEN_ENDPOINT,update_token=self.write_token)
        except Exception as e:
            logging.error('Could not load session')
            logging.exception(e)
            raise e
    
    def clean_symbol(self,symbol:str) -> str:
        return symbol.replace('.X','')


        
        
if(__name__ == '__main__'):
    logging.basicConfig(format='%(levelname)s - %(asctime)s: %(message)s',datefmt='%H:%M:%S', level=logging.DEBUG)
    client = Client()
    #client.setup() #Run this first then every 7 days
   
    qoute = client.get_Qoute('$SPX.X')
    print(qoute)

    clock = client.get_Clock()
    print(clock)

    chain = client.get_Option('$SPX.X',datetime.now())
    print(chain)
