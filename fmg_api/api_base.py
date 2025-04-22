#!/usr/bin/env python3

# fmg_api/api_base.py                                                        #
# Solution Deployer, Version 7.6.x b140                                      #
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
            payload), headers=headers, timeout=30, verify=False)

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
            if response: print(f"{response.request.method} {response.request.url}")
            print("Body:")
            print(json.dumps(request, indent=4))

            if response:
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

        response = None
        try:
            response = requests.request("POST", self.url, data=json.dumps(
                payload), headers=headers, timeout=30, verify=False)

            if not ApiSession.__is_request_status_ok(response):
                print(" \033[91mError in request.\033[0m")
                raise Exception(response.text)

            content = json.loads(response.content)

            if self.verbose: 
                ApiSession.__print_request_response(payload, response)

            print(" \033[92mCompleted\033[39m")
            return content
       
        except Exception as e:
            ApiSession.__print_request_response(payload, response)
            raise e


    def _run_request_async(self, payload, name=""):
        print("Running request \033[33m" + str(self.__request_number) +
              "\033[39m. \033[93m" + name + "\033[39m")
        self.__request_number += 1

        headers = {
            'Content-Type': "application/json",
            'cache-control': "no-cache"
        }

        response = None
        try:
            response = requests.request("POST", self.url, data=json.dumps(
                payload), headers=headers, timeout=30, verify=False)

            if not ApiSession.__is_request_status_ok(response):
                print(" \033[91mError in request.\033[0m")
                raise Exception(response.text)

            content = json.loads(response.content)
            try:
                task_id = content["result"][0]["data"]["taskid"]
            except:
                task_id = content["result"][0]["data"]["task"]

            if self.verbose: 
                ApiSession.__print_request_response(payload, response)

            print(" Asynchronous task created: " +
                str(task_id) + " ", end="", flush=False)
            while not self.__is_task_finished(task_id):
                print(".", end="", flush=True)
                sleep(5)

            print("\n \033[92mCompleted\033[39m")
            return content
        
        except Exception as e:
            ApiSession.__print_request_response(payload, response)
            raise e

    ##############################################################
    # API Session Management
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

    def getSessionCookie(self):
        return self._session

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
    # CLI Template Management
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
    # ADOM Management
    ##############################################################

    def deleteAdom(self, adom=None):

        payload = {
            "session": self._session,
            "id": 1,
            "method": "delete",
            "params": [
                {
                    "url": "/dvmdb/adom/" + (adom or self.adom)
                }
            ]
        }
        
        self._run_request(payload, name=f"Delete ADOM {adom or self.adom}")  

    ##############################################################
    # Device Management
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

    def resetAutoLink(self, dev_name, adom=None):
        pass

    ##############################################################
    # Task Management
    ##############################################################        

    @staticmethod
    def __parse_task(task):
        return {
            'id': int(task['id']),
            'title': task['title'],
            'success': task['state'] == 4,
            'completed': task['percent'] == 100,
            'dev_name': task['line'][0]['name'] if 'line' in task else '',
            'message': task['line'][0]['detail'] if 'line' in task else ''            
        }

    def getLastTasks(self, count=1, detailed=False):

        payload = {
            "session": self._session,
            "id": 1,
            "method": "get",
            "params": [
                {
                    "url": "/task/task",
                    "range": [
                        0,
                        count
                    ],
                    "sortings": [
                        {
                            "id": -1
                        }
                    ],
                    "loadsub": int(detailed)
                }
            ]
        }
        
        content = self._run_request(payload, name=f"Get Last Tasks (count = {count})") 
        tasks = []
        for t in content['result'][0]['data']:
            tasks.append(ApiSession.__parse_task(t))

        return tasks

    def getTask(self, id, detailed=False):

        payload = {
            "session": self._session,
            "id": 1,
            "method": "get",
            "params": [
                {
                    "url": "/task/task/" + str(id),
                    "loadsub": int(detailed)
                }
            ]
        }
        
        content = self._run_request(payload, name=f"Get Task {id}")
        return ApiSession.__parse_task(content['result'][0]['data'])