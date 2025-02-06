from datetime import datetime, timedelta
from methods.vault import VaultMethods
from methods.iris import IrisMethods
import requests
import logging
import time
import json
import yaml
import sys
import os

class MattermostMethods():

    def __init__(self):
        self.v = VaultMethods()
        self.iris = IrisMethods()
        self.polling_interval = 0
        self.mattermost = ''
        self.mentions = []
        self.commands = []
        self.username = ''
        self.bot_id = ''
        self.token = self.v.retrieve_mattermost_secrets()
        self.load_config()
        self.processed_mentions = {}
        self.mm_headers = {
            'Content-Type':'application/json',
            'Authorization':'Bearer {0}'.format(self.token)
        }
        self.command_options = {
            'cases': ['list', 'annotate', 'iocs', 'commentary', 'close'],
            'auth': ['status','renew'],
            'howto': ['commands']  
        }

    def load_config(self):
        try:
            config_dir = os.listdir('configuration')
            if 'mattermost.yaml' in config_dir:
                with open('configuration/mattermost.yaml', 'r') as f:
                    config = yaml.safe_load(f)
                    config = config['mattermost']
                    self.mattermost = config['fqdn']
                    self.channel = config['channel']
                    self.bot_id = config['user_id']
                    self.team_id = config['team_id']
                    self.username = config['username']
                    self.channel_id = config['channel_id']
                    self.polling_interval = config['polling_interval']
        except Exception as e:
            logging.exception("Failed to load Mattermost configuration")
            sys.exit(1)

    def get_users(self):
        try:
            response = requests.get(url="https://{0}/api/v4/users".format(self.mattermost),
                                    headers=self.mm_headers,
                                    verify=False)
            users = response.json()
            for user in users:
                logging.info("User: {0}".format(user))
            return users
        except Exception as e:
            logging.exception("Error retrieving users: {0}".format(e))
            return None
        
    def get_teams(self):
        try:
            response = requests.get(url="https://{0}/api/v4/teams".format(self.mattermost),
                                    headers=self.mm_headers,
                                    verify=False)
            teams = response.json()
            for team in teams:
                logging.info("Team: {0}".format(team))
                print()
            return teams
        except Exception as e:
            logging.exception("Error retrieving teams: {0}".format(e))
            return None
        
    def get_channels(self):
        try:
            response = requests.get(url="https://{0}/api/v4/channels".format(self.mattermost),
                                    headers=self.mm_headers,
                                    verify=False)
            channels = response.json()
            for channel in channels:
                logging.info("Channel: {0}".format(channel))
            return channels
        except Exception as e:
            logging.exception("Error retrieving channels: {0}".format(e))
            return None

    def post_message(self, message):
        try:
            payload = {
                "channel_id": self.channel_id,
                "message": message
            }
            response = requests.post(url="https://{0}/api/v4/posts".format(self.mattermost),
                                     headers=self.mm_headers,
                                     data=json.dumps(payload),
                                     verify=False)
            if response.status_code == 201:
                logging.info("Message posted")
            else:
                logging.error("Failed to post message: {0}".format(response.text))
        except Exception as e:
            logging.exception("Error posting message: {0}".format(e))

    def get_mentions(self):
        try:
            url = "https://{0}/api/v4/channels/{1}/posts".format(self.mattermost, self.channel_id)
            response = requests.get(url=url,
                                    headers=self.mm_headers,
                                    verify=False)
            if response.status_code == 200:
                posts = response.json().get('posts', {})
                now = datetime.now()
                interval = now - timedelta(minutes=self.polling_interval)
                mentions = []
                for post in posts.values():
                    post_time = datetime.fromtimestamp(post['create_at'] / 1000)
                    if f"@{self.username}" in post.get('message', '') and post_time > interval:
                        mentions.append(post['message'])
                for mention in mentions:
                    command_with_args = ' '.join(mention.split(' ')[1:])
                    self.mentions.append(command_with_args)
            else:
                logging.error("Failed to retrieve posts: {0} - {1}".format(response.status_code, response.text))
                self.mentions = []
        except Exception as e:
            logging.exception("Error retrieving mentions: {0}".format(e))
            return None
    
    def process_mentions(self):
        try:
            self.get_mentions()
            if self.mentions:
                now = datetime.now()
                for mention in self.mentions:
                    last_processed_time = self.processed_mentions.get(mention)
                    if not last_processed_time or (now - last_processed_time).total_seconds() > self.polling_interval * 60:
                        self.processed_mentions[mention] = now
                        command, *args = mention.split(' ')
                        if command.startswith('/'):
                            self.handle_command(command[1:], args)
                self.mentions.clear()
        except Exception as e:
            logging.exception("Error processing mentions")
            self.post_message({"channel_id": self.channel_id, "message": "Instruction processing failure"})
        finally:
            time.sleep(self.polling_interval)

    def handle_command(self, command, args):
        try:
            if command in self.command_options.keys():
                if command == 'cases':
                    if args[0] in self.command_options[command]:
                        if args[0] == 'list':
                            self.iris.get_open_cases()
                            for case in self.iris.cases:
                                print(case,'\n')
                                self.post_message("Case ID: {0}\nCase Title: {1}".format(case['case_id'], case['case_name']))
                        elif args[0] == 'annotate' and args[1].isdigit():
                            result = self.iris.annotate_case(args[1])
                            if result:
                                self.post_message("Case {0} annotated".format(args[1]))
                            else:
                                self.post_message("Failed to annotate case {0}".format(args[1]))
                        elif args[0] == 'annotate' and args[1] == 'all':
                            self.post_message("Adding commentary to all open cases")
                            result = self.iris.annotate_all_cases()
                            if result:
                                self.post_message("All cases annotated")
                            else:
                                self.post_message("Failed to annotate all cases")
                        elif args[0] == 'commentary':
                            notes = self.iris.get_case_notes(args[1])
                            self.post_message("Case {0} \n Analyst commentary: {1}".format(args[1], notes))
                        elif args[0] == 'iocs':
                            iocs = self.iris.get_case_iocs(args[1])
                            for ioc in iocs:
                                try:
                                    self.post_message("Case {0} \n IOC: {1}".format(args[1], ioc))
                                except Exception as e:
                                    self.post_message("Failed to post IOC: {0}".format(e))
                                    pass
                        elif args[0] == 'close' and args[1].isdigit():
                            result = self.iris.close_case(args[1])
                            if result:
                                self.post_message("Case {0} successfully closed".format(args[1]))
                            else:
                                self.post_message("Failed to close case {0}".format(args[1]))
                        elif args[0] == 'close' and args[1] == 'all':
                            result = self.iris.close_all_cases()
                            if result:
                                self.post_message("Successfully closed all cases")
                            else:
                                self.post_message("Failed to close all cases")
                    else:
                        self.post_message("Invalid command option")
                if command == 'auth':
                     if args[0] in self.command_options[command]:
                        if args[0] == 'status':
                            response = self.v.auth_check()
                            self.post_message("Authentication status: \n{0}".format(response))
                        elif args[0] == 'renew':
                            if self.v.renew_token():
                                self.post_message("Token renewed")
                            else:
                                self.post_message("Failed to renew token")
                        else:
                            self.post_message("Invalid command option")
                if command == 'howto':
                    if args[0] in self.command_options[command]:
                        if args[0] == 'commands':
                            for command in self.command_options.keys():
                                self.post_message("Command: /{0}".format(command))
                                for option in self.command_options[command]:
                                    self.post_message("- Option: {0}".format(option))
                        else:
                            self.post_message("Invalid command option")
            else:
                self.post_message("Invalid command")
        except Exception as e:
            logging.exception("Error handling command: {0}".format(e))


    
