#!/usr/bin/env python3

import os, glob, csv
from paramiko import SSHClient, AutoAddPolicy
from orch_base import *

def runPostmanTask(cfg, session, task):
    print(f"Running Postman collection - {task['folder']}...")
    command = getNewmanCommand(cfg, session)
    command.append(f"--folder \"{task['folder']}\"")
    if os.system(' '.join(command)): 
        raise Exception("Postman run ended with error(s)!")

def importCLITemplateTask(session, task):
    print(f"Importing CLI Templates from {task['src']}...")
    for t in glob.glob(task['src']):
        with open(t, 'r') as f:
            session.addCLITemplate(
                template_name = os.path.basename(os.path.splitext(t)[0]),
                content = f.read(),
                type = task.get('syntax', 'jinja')
            )

def createModelDevicesTask(session, task):
    print(f"Creating Model Devices from {task['src']}...")
    dev_list, vars = [], {}
    with open(task['src'], 'r', encoding='utf-8-sig') as f:
        for d in csv.DictReader(f):
            dev_name = d.pop('name')
            dev_list.append({
                "name": dev_name,
                "blueprint": d.pop('device blueprint'),
                "sn": d.pop('sn')
            })
            for k, v in d.items():
                vars.setdefault(k, {})
                vars[k][dev_name] = v
    print(f"Devices: {[dev['name'] for dev in dev_list]}")
    print(f"Variables: {[var for var in vars.keys()]}")
    session.addModelDevices(dev_list)
    session.setVariables(vars)
    session.assignCLITemplate("provision_interfaces_on_vm", dev_list)                

def onboardDevicesTask(cfg, task):
    print(f"Factory-resetting devices from {task['src']}...")
    print("NOTE: We won't wait until they finish ZTP process, so check it afterwards!")
    with open(task['src'], 'r', encoding='utf-8-sig') as f:
        dev_list = [ d['name'] for d in csv.DictReader(f) ]
    fail = 0
    for d in dev_list:
        print(f"--> {d}")
        fgt = cfg['sites'][d]
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        try:
            client.connect(
                fgt['ip'],
                port = fgt.get('port', 22),
                username = cfg['fgt_user'],
                password = cfg['fgt_password']
            )
            stdin, stdout, stderr = client.exec_command('execute factoryreset2 keepvmlicense\ny')
            stdout.read(20)
        except Exception as e:
            fail += 1
            print(f"\033[91m\033[1mFAILED:\033[0m {e}") 
        finally:
            client.close()
    if fail:
        raise Exception("At least some of the devices failed to onboard!")

def main():
    
    cfg = readConfig()
    session = getApiSession(cfg)
    
    print()
    print("Running automated deployment sequence...")

    success, fail = 0, 0
    for i, task in enumerate(cfg['tasks'], start=1):
        if fail and cfg.get('halt_on_fail', True):
            print(f"\033[91m\033[1mHALT ON FAIL:\033[0m Halting here, because the previous task has failed!") 
            break
        print()
        print(f"TASK {i}: {task['name']}")
        print("---------------------------------------------------")
        try:
            if task['type'] == 'postman':
                runPostmanTask(cfg, session, task)
            elif task['type'] == 'cli_templates':
                importCLITemplateTask(session, task)
            elif task['type'] == 'model_devices':
                createModelDevicesTask(session, task)
            elif task['type'] == 'onboard':
                if fail:
                    raise Exception("Skipping the onboarding, because (some of) the previous tasks failed!")
                onboardDevicesTask(cfg, task)
            success += 1
        except Exception as e:
            fail += 1
            print()
            print(f"\033[91m\033[1mTASK FAILED:\033[0m {e}") 

    print()
    print(f"All done! \033[32mSuccess: {success}\033[0m, \033[91mFail: {fail}\033[0m")


if __name__ == "__main__":
    main()    