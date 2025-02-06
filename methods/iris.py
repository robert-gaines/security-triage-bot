from methods.vault import VaultMethods
from methods.gpt import GPTMethods
from random import randint
import requests
import logging
import urllib3
import json
import yaml
import sys
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

class IrisMethods():

    def __init__(self):
        v = VaultMethods()
        self.g = GPTMethods()
        self.cms = ''
        self.cases = []
        self.customer = ''
        self.case_count = len(self.cases)
        self.load_config()
        self.cms_api_key = v.retrieve_iris_secrets()
        self.cms_headers = {
            'Content-Type':'application/json',
            'Authorization':'Bearer {0}'.format(self.cms_api_key)
        }
    
    def load_config(self):
        """ Load IRIS configuration """
        try:
            config_dir = os.listdir('configuration')
            if 'iris.yaml' in config_dir:
                with open('configuration/iris.yaml', 'r') as f:
                    config = yaml.safe_load(f)
                    config = config['iris']
                    self.cms = config['fqdn']
                    self.customer = config['customer']
        except Exception as e:
            logging.exception("Failed to load iris configuration")
            sys.exit(1)

    def get_open_cases(self) -> None:
        try:
            response = requests.get(url="https://{0}/manage/cases/list".format(self.cms),
                                    headers=self.cms_headers,
                                    verify=False)
            cases = response.json()['data']
            self.cases = [case for case in cases if case['state_name'] == 'Open']
            self.case_count = len(self.cases)
        except Exception as e:
            logging.exception("Error retrieving cases: {0}".format(e))
            return None
        
    def close_case(self, case_id) -> None:
        """ Close single DFIR IRIS case """
        try:
            response = requests.post(url="https://{0}/manage/cases/close/{1}".format(self.cms,case_id),
                                     headers=self.cms_headers,
                                     verify=False)
            if response.status_code == 200:
                logging.info("Case {0} closed".format(case_id))
                return True
            else:
                logging.info("Failed to close {0}".format(case_id))
                return False
        except Exception as e:
            logging.exception("Error closing case: {0}".format(e))
            return False
        
    def close_all_cases(self) -> None:
        """ Close all cases in DFIR IRIS """
        self.get_open_cases()
        try:
            for case in self.cases:
                self.close_case(case['case_id'])
            return True
        except Exception as e:
            return False

    def create_notes_directory(self, case_id, directory_name) -> str:
        """ Creates a note directory for case notes """
        try:
            payload = { "cid": case_id, "name": str(directory_name) }
            response = requests.post(url="https://{0}/case/notes/directories/add".format(self.cms),
                                     headers=self.cms_headers,
                                     data=json.dumps(payload),
                                     verify=False)
            if response.status_code == 200:
                return response.json()['data']['id']
            else:
                return None
        except Exception as e:
            return None

    def add_case_note(self,
                      case_id,
                      dir_id,
                      note_title,
                      note) -> bool:
        """ Add a note to a DFIR IRIS case directory """
        try:
            payload = { "cid": case_id, 
                        "note_title": str(note_title),
                        "note_content": str(note),
                        "directory_id": dir_id }
            response = requests.post(url="https://{0}/case/notes/add".format(self.cms),
                                     headers=self.cms_headers,
                                     data=json.dumps(payload),
                                     verify=False)
            if response.status_code == 200:
                return True
            else:
                return False
        except Exception as e:
            return False

    def get_case_notes(self, case_id) -> None:
        """ Retrieve notes from a DFIR IRIS case """
        try:
            response = requests.get(url="https://{0}/case/notes/directories/filter?cid={1}".format(self.cms,case_id),
                                    headers=self.cms_headers,
                                    verify=False)
            notes = response.json()['data']
            return notes
        except Exception as e:
            logging.exception("Error retrieving notes: {0}".format(e))
            return None

    def get_case_evidence(self, case_id) -> None:
        """ Retrieve evidence from a DFIR IRIS case """
        try:
            evidence_str = ''
            response = requests.get(url="https://{0}/case/evidences/list?cid={1}".format(self.cms,case_id),
                                    headers=self.cms_headers,
                                    verify=False)
            if response.status_code == 200:
                evidence = response.json()['data']['evidences']
                if evidence:
                    for item in evidence:
                        evidence_str += item['file_description'] + '\n'
                    return evidence_str
        except Exception as e:
            return None
        
    def annotate_case(self,case_id) -> bool:
        """ Annotate a DFIR IRIS case with GPT commentary """
        try:
            note_directory_id = self.create_notes_directory(case_id,"Analyst Commentary")
            evidence = self.get_case_evidence(case_id)
            commentary = self.g.create_completion(evidence)
            self.add_case_note(case_id,note_directory_id,"Analyst Commentary",commentary)
            return True
        except Exception as e:
            logging.exception("Error annotating case: {0}".format(e))
            return False
        
    def annotate_all_cases(self) -> bool:
        """ Annotate all DFIR IRIS cases with GPT commentary """
        self.get_open_cases()
        try:
            for case in self.cases:
                self.annotate_case(case['case_id'])
            return True
        except Exception as e:
            return False
        
    def get_case_notes(self, case_id) -> None:
        """ Retrieve notes from a DFIR IRIS case """
        try:
            response = requests.get(url="https://{0}/case/notes/directories/filter?cid={1}".format(self.cms,case_id),
                                    headers=self.cms_headers,
                                    verify=False)
            directories = response.json()['data']
            for directory in directories:
                for note in directory['notes']:
                    try:
                        response = requests.get(url="https://{0}/case/notes/{1}?cid={2}".format(self.cms,note['id'],case_id),
                                                headers=self.cms_headers,
                                                verify=False)
                        if response.status_code == 200:
                            data = response.json()['data']['note_content']
                            return data
                        else:
                            return "No commentary found"
                    except Exception as e:
                        pass
        except Exception as e:
            return None
        
    def get_case_iocs(self, case_id) -> str:
        try:
            response = requests.get(url="https://{0}/case/ioc/list?cid={1}".format(self.cms,case_id),
                                    headers=self.cms_headers,
                                    verify=False)
            iocs = response.json()['data']
            values = []
            for ioc in iocs['ioc']:
                values.append(ioc['ioc_value'])
            return values
        except Exception as e:
            return None


