#!/usr/bin/env python3

import os, glob, csv
from paramiko import SSHClient, AutoAddPolicy
from paramiko_expect import SSHClientInteraction
from yaml import safe_load
from fmg_api.api_base import ApiSession

def readConfig():

    print("========================")
    print(" Tenant: " + os.environ.get("ORCH_TENANT"))
    print("========================")
    tenantdir = "tenants/" + os.environ.get("ORCH_TENANT")

    with open(tenantdir + '/config.yaml', 'r') as cfgfile:
        cfg = safe_load(cfgfile)

    print("FMG Host = " + cfg['fmg_host'])
    print("ADOM = " + cfg['fmg_adom'])

    return cfg

def getApiSession(cfg):
    print("Connecting to FMG...")
    session = ApiSession(
        url = 'https://' + cfg['fmg_host'] + '/jsonrpc',
        adom = cfg['fmg_adom'],
        user = cfg['fmg_user'],
        password = cfg['fmg_password']
    )
    return session

def getNewmanCommand(cfg, session):
    command = []
    command.append('newman run')
    command.append('"' + cfg['postman_collection'] + '"')
    command.append('--insecure')
    command.append('--env-var "ip=' + cfg['fmg_host'] + '"')
    command.append('--env-var "username=' + cfg['fmg_user'] + '"')
    command.append('--env-var "password=' + cfg['fmg_password'] + '"')
    command.append('--env-var "adom=' + cfg['fmg_adom'] + '"')
    command.append('--env-var "session=' + session.getSessionCookie() + '"')
    return command


###################
# Deployment Tasks
###################

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
                type = task.get('syntax', 'jinja'),
                prerun = task.get('prerun', False)
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
    session.assignCLITemplate(task.get('prerun', 'provision_interfaces_on_vm'), dev_list)                

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
            print(f"Connecting to {fgt['ip']} with {cfg['fgt_user']} / {cfg['fgt_password']}")
            client.connect(
                fgt['ip'],
                port = fgt.get('port', 22),
                username = cfg['fgt_user'],
                password = cfg['fgt_password']
            )
            interact = SSHClientInteraction(client, display=True)
            interact.expect('.*# ')
            interact.send('execute factoryreset2 keepvmlicense')
            interact.expect('.*\(y/n\)')
            interact.send('y')
            interact.expect('.*')            
        except Exception as e:
            fail += 1
            print(f"\033[91m\033[1mFAILED:\033[0m {e}") 
        finally:
            client.close()
    if fail:
        raise Exception("At least some of the devices failed to onboard!")