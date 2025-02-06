from methods.vault import VaultMethods
import requests
import logging
import json
import yaml
import sys
import os

class GPTMethods():

    def __init__(self):
        v = VaultMethods()
        token = v.retrieve_gpt_secrets()
        self.headers = {
            'Authorization': 'Bearer {0}'.format(token),
            'Content-Type': 'application/json'
        }
        self.load_config()

    def load_config(self) -> None:
        """ Load GPT configuration """
        try:
            config_dir = os.listdir('configuration')
            if 'gpt.yaml' in config_dir:
                with open('configuration/gpt.yaml', 'r') as f:
                    config = yaml.safe_load(f)
                    config = config['gpt']
                    self.model = config['model']
                    self.modality = config['modality']
                    self.effort = config['effort']
                    self.role = config['role']
                    self.content = config['content']
                    self.n = config['n']
        except Exception as e:
            logging.exception("Failed to load GPT configuration")
            sys.exit(1)

    def list_models(self):
        """ List available GPT models """
        try:
            response = requests.get(url="https://api.openai.com/v1/models",
                                    headers=self.headers)
            models = response.json()['data']
            for model in models:
                logging.info("Model: {0}".format(model))
        except Exception as e:
            logging.exception("Error listing models: {0}".format(e))
            return None
        
    def create_completion(self, prompt) -> str:
        """ Generate completion using the GPT cmopletion endpoint """
        try:
            self.content += prompt
            payload = {
                "model": self.model,
                'messages':[ {
                    'role': self.role,
                    'content': self.content,
                }],
                'n': self.n,
                'modalities': self.modality,
            }
            response = requests.post(url="https://api.openai.com/v1/chat/completions",
                                    headers=self.headers,
                                    data=json.dumps(payload))
            completion = response.json()['choices'][0]['message']['content']
            return completion
        except Exception as e:
            logging.exception("Error creating completion: {0}".format(e))
            return None