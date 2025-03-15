#!/usr/bin/env python3

# fmg_api/api_base.py                                                        #
# Solution Deployer, Version 7.6.x b120                                      #
# -------------------------------------------------------------------------- #
# Maintainers: CSE Telco/MSSP EMEA, Fortinet (internal use only)             #
# -------------------------------------------------------------------------- #

import requests
import json

from urllib3.exceptions import InsecureRequestWarning
from time import sleep
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

class ApiSession:

    _session = None
    __request_number = 0

    verbose = False

    def __init__(self, url, adom, user, password):
        self.url = url
        self.adom = adom
        self.login(user, password)

    def __del__(self):
        self.verbose = False
        self.logout()

    def __is_task_finished(self, id):

        payload = {
            "session": self._session,
            "id": 1,
            "method": "get",
            "params": [
                {
                    "url": "/task/task/" + str(id)
                }
            ]
        }

        headers = {
            'Content-Type': "application/json",
            'cache-control': "no-cache"
        }

        response = requests.request("POST", self.url, data=json.dumps(
            payload), headers=headers, verify=False)

        if not self.__is_request_status_ok(response):
            print(" \033[31Error in request.\033[39m")
            print(response.text)
            raise Exception(response.text)

        try:
            content = json.loads(response.content)
            line = content["result"][0]["data"]["line"]

            for l in line:
                if l["percent"] != 100:
                    return False
        except:
            content = json.loads(response.content)
            if content["result"][0]["data"]["percent"] != 100:
                return False

        return True


    @staticmethod
    def __is_request_status_ok(response):
        content = json.loads(response.content)

        return response.status_code == 200 and \
            content["result"][0]["status"]["code"] == 0 and \
            content["result"][0]["status"]["message"] == "OK"


    @staticmethod
    def __print_request_response(request, response):

        try:
            print("\033[2m")
            print("---- Request ----")
            print(f"{response.request.method} {response.request.url}")
            print("Body:")
            print(json.dumps(request, indent=4))

            print("\n---- Response ----")
            print(f"Status Code: {response.status_code}")
            print("Body:")
            print(json.dumps(response.json(), indent=4))

        finally:
            print("\033[0m")


    def _run_request(self, payload, name=""):
        print("Running request \033[33m" + str(self.__request_number) +
              "\033[39m. \033[93m" + name + "\033[39m")
        self.__request_number += 1

        headers = {
            'Content-Type': "application/json",
            'cache-control': "no-cache"
        }

        response = requests.request("POST", self.url, data=json.dumps(
            payload), headers=headers, verify=False)

        if self.verbose or not ApiSession.__is_request_status_ok(response): 
            ApiSession.__print_request_response(payload, response)
        if not ApiSession.__is_request_status_ok(response):
            print(" \033[91mError in request.\033[0m")
            raise Exception(response.text)

        content = json.loads(response.content)

        print(" \033[92mCompleted\033[39m")
        return content


    def _run_request_async(self, payload, name=""):
        print("Running request \033[33m" + str(self.__request_number) +
              "\033[39m. \033[93m" + name + "\033[39m")
        self.__request_number += 1

        headers = {
            'Content-Type': "application/json",
            'cache-control': "no-cache"
        }

        response = requests.request("POST", self.url, data=json.dumps(
            payload), headers=headers, verify=False)

        if self.verbose or not ApiSession.__is_request_status_ok(response): 
            ApiSession.__print_request_response(payload, response)
        if not ApiSession.__is_request_status_ok(response):
            print(" \033[91mError in request.\033[0m")
            raise Exception(response.text)

        content = json.loads(response.content)
        try:
            task_id = content["result"][0]["data"]["taskid"]
        except:
            task_id = content["result"][0]["data"]["task"]

        print(" Asynchronous task created: " +
              str(task_id) + " ", end="", flush=False)
        while not self.__is_task_finished(task_id):
            print(".", end="", flush=True)
            sleep(5)

        print("\n \033[92mCompleted\033[39m")
        return content

    ##############################################################
    # Login
    ##############################################################
    def login(self, user, password):

        payload = {
            "session": 1,
            "id": 1,
            "method": "exec",
            "params": [
                {
                    "url": "sys/login/user",
                    "data": [
                        {
                            "user": user,
                            "passwd": password
                        }
                    ]
                }
            ]
        }

        content = self._run_request(payload, "Login")
        self._session = content["session"]

    ##############################################################
    # Get Session Coockie
    ##############################################################
    def getSessionCookie(self):
        return self._session

    ##############################################################
    # Logout
    ##############################################################
    def logout(self):

        payload = {
            "session": self._session,
            "id": 1,
            "method": "exec",
            "params": [
                {
                    "url": "sys/logout"
                }
            ]
        }

        content = self._run_request(payload, "Logout")
        self._session = None

    ##############################################################
    # Get Serial Number
    ##############################################################
    def getSerialNumber(self):

        payload = {
            "session": self._session,
            "id": 1,
            "method": "get",
            "params": [
                {
                    "url": "sys/status"
                }
            ]
        }

        content = self._run_request(payload, "Get Serial Number")
        return content['result'][0]['data']['Serial Number']

    ##############################################################
    # Add CLI Template
    ##############################################################
    def addCLITemplate(self, template_name, content, type='cli', prerun=False):

        payload = {
            "session": self._session,
            "id": 1,
            "method": "set",
            "params": [
                {
                    "url": "/pm/config/adom/" + self.adom + "/obj/cli/template",
                    "data": [
                        {
                            "name": template_name,
                            "provision": prerun,
                            "type": type,
                            "script": content
                        }
                    ]
                }
            ]
        }

        self._run_request(payload, name=f"Add CLI Template ({template_name})")

    ##############################################################
    # Assign CLI Template
    ##############################################################
    def assignCLITemplate(self, template_name, dev_list):

        scope_dev_list = []
        for d in dev_list:
            scope_dev_list.append({
                "name": d['name'],
                "vdom": "global"
            })

        payload = {
            "session": self._session,
            "id": 1,
            "method": "add",
            "params": [
                {
                    "url": "/pm/config/adom/" + self.adom + "/obj/cli/template/" + template_name + "/scope member",
                    "data": scope_dev_list
                }
            ]
        }
        
        self._run_request(payload, name=f"Assign CLI Template ({template_name})")

    ##############################################################
    # Add Model Devices
    ##############################################################
    def addModelDevices(self, dev_list):

        add_dev_list = []
        for dev in dev_list:
            add_dev_list.append({
                "name": dev['name'],
                "device action": "add_model",
                "mgmt_mode": 3,
                "device blueprint": dev['blueprint'],
                "sn": dev['sn'],
                "os_type": 0,
                "os_ver": dev.get('os_ver', 7),
                "mr": dev.get('os_mr', 4),
                "adm_usr": "admin"
            })

        payload = {
            "session": self._session,
            "id": 1,
            "method": "exec",
            "params": [
                {
                    "url": "/dvm/cmd/add/dev-list",
                    "data": {
                        "adom": self.adom,
                        "flags": [ "create_task", "nonblocking" ],
                        "add-dev-list": add_dev_list
                    }
                }
            ]
        }
        
        self._run_request_async(payload, name="Add Model Devices")

    ##############################################################
    # Delete Devices
    ##############################################################
    def deleteDevices(self, dev_list, adom=None):

        if not dev_list: return
        
        del_dev_list = []
        for dev in dev_list:
            del_dev_list.append({
                "name": dev['name'],
                "vdom": "root"
            })
        
        payload = {
            "session": self._session,
            "id": 1,
            "method": "exec",
            "params": [
                {
                    "url": "/dvm/cmd/del/dev-list",
                    "data": {
                        "adom": adom or self.adom,
                        "del-dev-member-list": del_dev_list
                    }
                }
            ]
        }
        
        self._run_request(payload, name=f"Delete Devices from {adom or self.adom}")  

    ##############################################################
    # Set Variables
    ##############################################################
    def setVariables(self, vars):

        var_list = []
        for var, map in vars.items():
            map_list = []
            for dev, val in map.items():
                map_list.append({
                    "_scope": [
                        {
                            "name": dev,
                            "vdom": "global"
                        }
                    ],
                    "value": val
                })
            var_list.append({
                "name": var,
                "dynamic_mapping": map_list
            })

        payload = {
            "session": self._session,
            "id": 1,
            "method": "set",
            "params": [
                {
                    "url": "/pm/config/adom/" + self.adom + "/obj/fmg/variable",
                    "data": var_list
                }
            ]
        }
        
        self._run_request(payload, name="Set Variables")        

    ##############################################################
    # Get Devices
    ##############################################################

    def getDevices(self, adom=None):

        payload = {
            "session": self._session,
            "id": 1,
            "method": "get",
            "params": [
                {
                    "url": "/dvmdb/adom/" + (adom or self.adom) + "/device",
                    "fields": [
                        "name",
                        "ip",
                        "platform_str"
                    ]
                }
            ]
        }

        content = self._run_request(payload, name=f"Get Devices in {adom or self.adom}")
        dev_list = []
        for dev in content['result'][0]['data']:
            dev_list.append(
                {
                    'name': dev['name'],
                    'ip': dev['ip'],
                    'platform_str': dev['platform_str']
                }
            )

        return dev_list

    ##############################################################
    # Get Device
    ##############################################################

    def getDevice(self, dev_name, adom=None):

        payload = {
            "session": self._session,
            "id": 1,
            "method": "get",
            "params": [
                {
                    "url": "/dvmdb/adom/" + (adom or self.adom) + "/device",
                    "filter": [
                        "name",
                        "==",
                        dev_name
                    ],
                    "fields": [
                        "name",
                        "ip",
                        "platform_str"
                    ]
                }
            ]
        }

        content = self._run_request(payload, name=f"Get Device {dev_name} in {adom or self.adom}")
        if (content['result'][0]['data']):
            dev = content['result'][0]['data'][0]
            return {
                'name': dev['name'],
                'ip': dev['ip'],
                'platform_str': dev['platform_str']
            }
        else:
            return False
