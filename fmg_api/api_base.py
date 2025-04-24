#!/usr/bin/env python3

# fmg_api/api_base.py                                                        #
# Solution Deployer, Version 7.6.x                                           #
# -------------------------------------------------------------------------- #
# Maintainers: CSE Telco/MSSP EMEA, Fortinet (internal use only)             #
# -------------------------------------------------------------------------- #

import requests
import json

from urllib3.exceptions import InsecureRequestWarning
from time import sleep
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

class ApiSession:
    """Wraps API communication with the FMG."""

    _session = None
    __request_number = 0

    verbose = False
    """print every json request and response"""

    def __init__(self, url: str, adom: str, user: str, password: str):
        self.url = url
        self.adom = adom
        self.login(user, password)

    def __del__(self):
        self.verbose = False
        self.logout()


    ##############################################################
    # API Session Management
    ##############################################################

    def login(self, user: str, password: str):
        """Login to FMG and obtain an API session cookie."""

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


    def getSessionCookie(self) -> str:
        return self._session


    def logout(self):
        """Logout from FMG, destroy API session."""

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

        self._run_request(payload, "Logout")
        self._session = None


    def getSerialNumber(self) -> str:
        """Get FMG Serial Number."""

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

    def addCLITemplate(self, template_name: str, content: str, type='cli', prerun=False):
        """Import CLI Template (type = 'cli' or 'jinja')."""

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


    def assignCLITemplate(self, template_name: str, dev_list: list[dict]):
        """Assign CLI Template to device(s).

        Args:

            dev_list: [ 
                { 
                    'name' (str): device name
                },
                ...
            ]
        """

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

    def deleteAdom(self, adom: str=None):
        """Delete ADOM."""

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

    def addModelDevices(self, dev_list: dict):
        """Add a list of Model Devices.

        Args:

            dev_list: [
                {
                    'name' (str): device name,
                    'blueprint' (str): device blueprint,  
                    'sn' (str): serial number,  
                    'os_ver' (str, optional): major FOS version, default = 7,
                    'os_mr' (str, optional): minor FOS version, default = 6  
                },  
                ...
            ]
        """

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
                "mr": dev.get('os_mr', 6),
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


    def getDevices(self, adom: str=None) -> list[dict]:
        """Get all devices in ADOM.
        
        Returns:

            list[dict]: [
                {
                    'name' (str): device name,  
                    'ip' (str): device IP,  
                    'platform_str' (str): device platform 
                }, 
                ...
            ]
        """        

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


    def getDevice(self, dev_name: str, adom=None) -> dict:
        """Get device by name.
        
        Returns:

            dict: {
                'name' (str): device name,  
                'ip' (str): device IP,  
                'platform_str' (str): device platform
            }
        """

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
            return None


    def deleteDevices(self, dev_list: list[dict], adom=None):
        """Delete devices. 

        Args:

            dev_list: [ 
                { 
                    'name' (str): device name
                },
                ...
            ]
        """
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


    def setVariables(self, vars: dict[str, dict[str,str]]):
        """Set metadata variables for multiple devices.

        Args:

            vars: {
                var1: {
                    dev1: val11,
                    dev2: val12,
                    ...
                }, 
                var2: {
                    dev1: val21,
                    dev2: val22,
                    ...
                },
                ...
            }
        """

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


    def resetAutoLink(self, dev_name: str):
        """Reset Auto-Link for requested device (by resetting FGFM tunnel)."""

        payload = {
            "session": self._session,
            "id": 1,
            "method": "exec",
            "params": [
                {
                    "url": "/cli/global/exec/fgfm/reclaim-dev-tunnel/" + dev_name,
                    "data": {
                        "flags": [
                            "force"
                        ]
                    }                    
                }
            ]
        }
        
        self._run_request(payload, name=f"Reset Auto-Link for {dev_name}")  


    ##############################################################
    # Task Management
    ##############################################################        

    @staticmethod
    def __parse_task(task: str) -> dict:
        return {
            'id': int(task['id']),
            'title': task['title'],
            'success': task['state'] == 4,
            'completed': task['percent'] == 100,
            'dev_name': task['line'][0]['name'] if 'line' in task else '',
            'message': task['line'][0]['detail'] if 'line' in task else ''            
        }


    def getLastTasks(self, count=1, detailed=False) -> list[dict]:
        """Get the requested number of last FMG tasks.

        Returns:

            list[dict]: [
                {
                    'id' (int): task id,  
                    'title' (str): task title,   
                    'success' (bool): successful (True/False),  
                    'completed' (bool): completed (True/False),  
                    'dev_name' (str): device name (only in detailed mode),  
                    'message' (str): last message (only in detailed mode) 
                },
                ...
            ]
        """

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


    def getTask(self, id: int, detailed=False, silent=False) -> dict:
        """Get FMG task by ID.
        
        Returns:

            dict: {
                'id' (int): task id,  
                'title' (str): task title,  
                'success' (bool): successful (True/False),  
                'completed' (bool): completed (True/False),  
                'dev_name' (str): device name (only in detailed mode),  
                'message' (str): last message (only in detailed mode)  
            }
        """

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
        
        content = self._run_request(payload, name=f"Get Task {id}", silent=silent)
        return ApiSession.__parse_task(content['result'][0]['data'])


    ##############################################################
    # Backend (API communication)
    ##############################################################  

    @staticmethod
    def __is_request_status_ok(response) -> bool:
        content = json.loads(response.content)

        return response.status_code == 200 and \
            content["result"][0]["status"]["code"] == 0 and \
            content["result"][0]["status"]["message"] == "OK"


    @staticmethod
    def __print_request_response(request, response):
        """Print JSON request/response"""

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


    def _run_request(self, payload, name="", silent=False):
        """Send API call and return the response."""

        silent or print("Running request \033[33m" + str(self.__request_number) +
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
                silent or print(" \033[91mError in request.\033[0m")
                raise Exception(response.text)

            content = json.loads(response.content)

            if self.verbose: 
                silent or ApiSession.__print_request_response(payload, response)

            silent or print(" \033[92mCompleted\033[39m")
            return content
       
        except Exception as e:
            silent or ApiSession.__print_request_response(payload, response)
            raise e


    def _run_request_async(self, payload, name="", silent=False):
        """Send asynchronous API call, get FMG task_id and wait until the task completes."""

        silent or print("Running request \033[33m" + str(self.__request_number) +
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
                silent or print(" \033[91mError in request.\033[0m")
                raise Exception(response.text)

            content = json.loads(response.content)
            try:
                task_id = content["result"][0]["data"]["taskid"]
            except:
                task_id = content["result"][0]["data"]["task"]

            if self.verbose: 
                silent or ApiSession.__print_request_response(payload, response)

            silent or print(" Asynchronous task created: " +
                str(task_id) + " ", end="", flush=False)
            
            retries=30
            while retries and not (task_status := self.getTask(task_id, silent=True))['completed']:
                silent or print(".", end="", flush=True)
                sleep(5)
                retries -= 1
            
            if not retries: 
                silent or print("\n \033[91mAsynchronous task has failed to complete.\033[0m")
                raise Exception(f"Asynchronous task failed to complete, taskid={task_status['id']}")
            elif not task_status['success']:
                task_status = self.getTask(task_id, detailed=True, silent=True)
                silent or print("\n \033[91mAsynchronous task has completed with error.\033[0m")
                raise Exception(f"Asynchronous task completed with error: {task_status['message']}")
            else:
                silent or print("\n \033[92mCompleted\033[39m")
                return content
        
        except Exception as e:
            silent or ApiSession.__print_request_response(payload, response)
            raise e
    