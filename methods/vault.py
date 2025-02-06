import requests
import logging
import urllib3
import yaml
import sys
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

class VaultMethods():

    def __init__(self):
        self.vault_url = ''
        self.vault_token = ''
        self.token_renew_buffer = 0
        self.iris_token_path = ""
        self.gpt_token_path = ""
        self.iris_key = ""
        self.gpt_key = ""
        self.load_config()
        self.headers = {
            'X-Vault-Token': self.vault_token
        }
        try:
            if not self.is_authenticated():
                logging.info("Vault authentication failed")
                sys.exit(1)
            if self.check_seal_status():
                logging.info("Vault is sealed")
                sys.exit(1)
            if self.check_token() < self.token_renew_buffer:
                self.renew_token()
        except Exception as e:
            logging.exception("Failed to communicate with vault")
            sys.exit(1)

    def load_config(self) -> None:
        '''Load vault configuration'''
        try:
            config_dir = os.listdir('configuration')
            if 'vault.yaml' in config_dir:
                with open('configuration/vault.yaml', 'r') as f:
                    config = yaml.safe_load(f)
                    config = config['vault']
                    self.vault_url = "https://{0}".format(config['fqdn'])
                    self.vault_token = config['token']
                    self.token_renew_buffer = config['buffer']
                    self.iris_token_path = config['iris_token_path']
                    self.mattermost_token_path = config['mattermost_token_path']
                    self.gpt_token_path = config['gpt_token_path']
            else:
                logging.error("Vault configuration file not found")
                sys.exit(1)
        except Exception as e:
            logging.exception("Failed to load vault configuration")
            sys.exit(1)

    def is_authenticated(self) -> bool:
        '''Check if the client is authenticated'''
        try:
            response = requests.get(f"{self.vault_url}/v1/auth/token/lookup-self", headers=self.headers, verify=False)
            return response.status_code == 200
        except Exception as e:
            logging.exception(e)
            return False
        
    def check_token(self) -> int:
        '''Check token TTL'''
        try:
            response = requests.get(f"{self.vault_url}/v1/auth/token/lookup-self", headers=self.headers, verify=False)
            token = response.json()
            return token['data']['ttl']
        except Exception as e:
            logging.exception(e)
            sys.exit(1)

    def check_seal_status(self) -> bool:
        '''Check to see if the vault is sealed'''
        try:
            response = requests.get(f"{self.vault_url}/v1/sys/seal-status", headers=self.headers, verify=False)
            seal_status = response.json()
            return seal_status['sealed']
        except Exception as e:
            logging.exception(e)
            sys.exit(1)

    def renew_token(self) -> None:
        '''Renew period token'''
        try:
            response = requests.post(f"{self.vault_url}/v1/auth/token/renew-self", headers=self.headers, verify=False)
            renewal_response = response.json()
            logging.info(renewal_response)
            ttl = renewal_response['auth']['lease_duration']
            logging.info(f"Token renewed. New TTL: {ttl} seconds")
        except Exception as e:
            logging.exception(f"Error renewing token: {e}")

    def retrieve_iris_secrets(self) -> str:
        '''Retrieve IRIS API token'''
        try:
            response = requests.get(f"{self.vault_url}/v1/{self.iris_token_path}", headers=self.headers, verify=False)
            response = response.json()['data']['data']['token']
            self.iris_key = response
            return self.iris_key
        except Exception as e:
            logging.exception(f"Error retrieving Iris secret: {e}")
            return None
        
    def retrieve_gpt_secrets(self) -> str:
        '''Retrieve GPT API token'''
        try:
            response = requests.get(f"{self.vault_url}/v1/{self.gpt_token_path}", headers=self.headers, verify=False)
            response = response.json()['data']['data']['key']
            self.gpt_key = response
            return self.gpt_key
        except Exception as e:
            logging.exception(f"Error retrieving GPT secret: {e}")
            return None
        
    def retrieve_mattermost_secrets(self) -> str:
        '''Retrieve Mattermost API token'''
        try:
            response = requests.get(f"{self.vault_url}/v1/{self.mattermost_token_path}", headers=self.headers, verify=False)
            response = response.json()['data']['data']['key']
            self.mattermost_key = response
            return self.mattermost_key
        except Exception as e:
            logging.exception(f"Error retrieving Mattermost secret: {e}")
            return None
        
    def auth_check(self) -> str:
        """Check authentication status"""
        try:
            seal_status = self.check_seal_status()
            auth_status = self.is_authenticated()
            token_status = self.check_token()
            response = f"Seal Status: {seal_status}\nAuth Status: {auth_status}\nToken TTL: {token_status}"
            logging.info(response)
            return response
        except Exception as e:
            return e
        
    def renew_token(self) -> None:
        """Renew token"""
        try:
            response = requests.post(url=f"{self.vault_url}/v1/auth/token/renew-self",
                                     headers=self.headers,
                                     verify=False)
            if response.status_code == 200:
                return True
            else:
                return False
        except Exception as e:
            return False