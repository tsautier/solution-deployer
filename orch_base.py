#!/usr/bin/env python3

# orch_base.py                                                               #
# Solution Deployer, Version 7.6.x b140                                      #
# -------------------------------------------------------------------------- #
# Maintainers: CSE Telco/MSSP EMEA, Fortinet (internal use only)             #
# -------------------------------------------------------------------------- #

import os, glob, csv, jinja2
from time import sleep
from pathlib import Path
from paramiko import SSHClient, AutoAddPolicy, ssh_exception
from paramiko_expect import SSHClientInteraction
from yaml import safe_load
from fmg_api.api_base import ApiSession
from helpers import print_table

def readConfig(shared=False, silent=False) -> dict:
    """Reads config.yaml

    Args:
        shared (bool, optional): 
            Use False to read the current tenant config (as specified by env.var ORCH_TENANT or .orch_tenant file). 
            Use True to read the shared config. Defaults to False.
        silent (bool, optional): Suppress outputs. Defaults to False.

    Returns:
        dict: config dictionary
    """
    if not shared:
        tenant = os.environ.get("ORCH_TENANT") or \
            (Path('.orch_tenant').read_text().strip() if Path('.orch_tenant').exists() else "")

        silent or print("========================")
        silent or print(" Tenant: " + tenant)
        silent or print("========================")
    else:
        # Read shared configs
        tenant = 'shared'

    tenantdir = "tenants/" + tenant

    with open(tenantdir + '/config.yaml', 'r') as cfgfile:
        cfg = safe_load(cfgfile)

    # Optional locally stored secrets (tenant file overrides shared file)
    secrets = tenantdir + '/.secrets.yaml'
    if not shared and not Path(secrets).exists():
        # Tenant file doesn't exist, try shared file
        secrets = "tenants/shared/.secrets.yaml"
    if Path(secrets).exists():
        with open(secrets, 'r') as secrets_file:
            cfg = cfg | safe_load(secrets_file)

    if not shared:
        silent or print("FMG Host = " + cfg['fmg_host'])
        silent or print("ADOM = " + cfg['fmg_adom'])

    cfg['tenant'] = tenant
    cfg['tenantdir'] = tenantdir

    return cfg

def getApiSession(cfg, silent=False):
    silent or print("Connecting to FMG...")
    session = ApiSession(
        url = 'https://' + cfg['fmg_host'] + '/jsonrpc',
        adom = cfg['fmg_adom'],
        user = cfg['fmg_user'],
        password = cfg['fmg_password']
    )
    return session

def setNewPassword(client, fgt, cfg, silent=False):
    silent or print(f"Connecting to {fgt['ip']} with {cfg['fgt_user']} and trying to set the new password to {cfg['fgt_password']}")
    client.connect(
        fgt['ip'],
        port = fgt.get('port', 22),
        username = cfg['fgt_user'],
        password = ""
    )            
    interact = SSHClientInteraction(client, display=(not silent))
    silent or print('>')
    interact.expect('New Password: ')
    interact.send(cfg['fgt_password'])
    interact.expect('Confirm Password: ')
    interact.send(cfg['fgt_password'])
    interact.expect('.*# ')    
    silent or print('<')       
    silent or print("The new password has been set successfully!")  

def getSystemStatus(output):
    dict = {}
    for str in [ s for s in output if ':' in s ]:
        k,v = str.split(':', 1)
        if len(k.split('#')) > 1: k = k.split('#')[-1]
        dict[k.strip()] = v.strip()
    return dict

###################
# Deployment Tasks
###################

def runPostmanTask(cfg, session, task, silent=False):
    silent or print(f"Running Postman collection - {task['folder']}...")
    vars = {}
    if 'vars' in task:
        with open(task['vars'], 'r') as varfile:
            vars = safe_load(varfile)
    command = __getNewmanCommand(cfg, session, vars, silent)
    command.append(f"--folder \"{task['folder']}\"")
    if os.system(' '.join(command)): 
        raise Exception("Postman run ended with error(s)!")

def importCLITemplateTask(session, task, silent=False):
    silent or print(f"Importing CLI Templates from {task['src']}...")
    for t in glob.glob(task['src']):
        with open(t, 'r') as f:
            session.addCLITemplate(
                template_name = task.get('rename', os.path.basename(os.path.splitext(t)[0])),
                content = f.read(),
                type = task.get('syntax', 'jinja'),
                prerun = task.get('prerun', False)
            )

def deleteDevicesTask(session, task, silent=False):
    silent or print(f"Deleting Devices from {task['adom']}...")
    session.deleteDevices(
        session.getDevices(adom=task['adom']),
        adom=task['adom']
    )

def createModelDevicesTask(session, task, silent=False):
    silent or print(f"Creating Model Devices from {task['src']}...")
    dev_list, vars = [], {}
    with open(task['src'], 'r', encoding='utf-8-sig') as f:
        for d in csv.DictReader(f):
            dev_name = d.pop('Name')
            fos_ver = str(task.get('fos', '7.4'))
            dev_list.append({
                "name": dev_name,
                "blueprint": d.pop('Device Blueprint'),
                "sn": d.pop('Serial Number'),
                "os_ver": int(fos_ver.split('.')[0]),
                "os_mr": int(fos_ver.split('.')[1])
            })
            for k, v in d.items():
                if v:
                    vars.setdefault(k, {})
                    vars[k][dev_name] = v
    silent or print(f"Devices: {[dev['name'] for dev in dev_list]}")
    silent or print(f"Variables: {[var for var in vars.keys()]}")
    session.deleteDevices(
        session.getDevices('root'),
        adom='root'
    )    
    session.addModelDevices(dev_list)
    session.setVariables(vars)
    if 'prerun' in task:
        session.assignCLITemplate(task['prerun'], dev_list)        

def onboardDevicesTask(cfg, task, session=None, silent=False):
    if 'src' in task:
        silent or print(f"Factory-resetting devices from {task['src']}...")
        with open(task['src'], 'r', encoding='utf-8-sig') as f:
            dev_list = [ d['Name'] for d in csv.DictReader(f) ]
    elif 'site' in task:
        silent or print(f"Factory-resetting device {task['site']}...")
        dev_list = [ task['site'] ]
    else:
        silent or print("Factory-resetting all tenant devices...")
        dev_list = cfg['sites'].keys()

    lastFMGTask = 0
    if task.get('monitor', False):
        silent or print("ZTP Monitoring requested, noting the last FMG Task ID...")
        lastFMGTask = session.getLastTasks()[0]['id']
        
    fail = 0
    for d in dev_list:
        silent or print(f"--> {d}")
        if not __runOnDevice(
            fgt = cfg['sites'][d],
            action = __factoryResetDevice,
            cfg = cfg,
            silent = silent
        ): fail+=1

    if fail:
        raise Exception("At least some of the devices failed to onboard!")
    elif task.get('monitor', False):
        fail, ztp_tasks = __monitorZTP(session, dev_list, lastFMGTask, silent)
        if fail and task.get('retry', False):
            silent or print()
            silent or print("ZTP process has failed for some of the devices.")
            silent or print("ZTP recovery attempt requested, noting the last FMG Task ID...")
            failed_dev_list = [ t['dev_name'] for t in ztp_tasks if t['completed'] and not t['success'] ]
            lastFMGTask = session.getLastTasks()[0]['id']
            for d in failed_dev_list: 
                session.resetAutoLink(d)
            fail, ztp_tasks = __monitorZTP(session, failed_dev_list, lastFMGTask, silent)
        if fail:
            raise Exception("ZTP process has failed for some of the devices!")
    else:
        silent or print("NOTE: We won't wait until the ZTP process completes, so check it afterwards!")

def runCLICommandTask(cfg, task, silent=False):
    silent or print(f"Running CLI on {task['site']}...")
    silent or print(f"CLI: {task['cli']}")
    output = __runOnDevice(
        fgt = cfg['sites'][task['site']],
        action = __applyCLIConfig,
        cfg = cfg,
        action_args = task['cli'],
        silent = silent
    )
    if not output:
        raise Exception("Failed to run CLI!")
    return output

def applyCLIConfigTask(cfg, task, silent=False):
    todo = {}
    if 'site' in task and len(glob.glob(task['src'])) == 1:
        silent or print(f"Running CLI from {task['src']} on {task['site']}...")
        todo[task['site']] = task['src']
    elif 'src' in task:
        silent or print(f"Running CLI from {task['src']} on respective devices...")
        for c in glob.glob(task['src']):
            d = os.path.basename(os.path.splitext(c)[0])
            todo[d] = c

    fail = 0
    for d,c in todo.items():
        silent or print(f"--> {d}")
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.dirname(c)),
            undefined=jinja2.StrictUndefined
        )
        rendered = env.get_template(os.path.basename(c)).render(task.get('vars', {}))
        silent or print(rendered)
        if not __runOnDevice(
            fgt = cfg['sites'][d],
            action = __applyCLIConfig,
            cfg = cfg,
            action_args = rendered,
            silent = silent
        ): fail+=1
    
    if fail:
        raise Exception("Failed to apply CLI config to at least some of the devices!")

###################
# Helper Functions
###################

def __runOnDevice(fgt, action, cfg, action_args=None, silent=False):
    output = None
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    try:
        output = action(client, fgt, cfg, action_args, silent)
    except ssh_exception.AuthenticationException as e:
        silent or print(f"\033[91m\033[1mAuthentication failed,\033[0m trying an empty password (in case it is not set yet)...") 
        try:
            setNewPassword(client, fgt, cfg, silent)
            output = action(client, fgt, cfg, action_args, silent)
        except ssh_exception.AuthenticationException as e:
            silent or print(f"\033[91m\033[1mFAILED:\033[0m {e}") 
    except Exception as e:
        print(f"\033[91m\033[1mFAILED:\033[0m {e}") 
    finally:
        client.close()

    return output

def __factoryResetDevice(client, fgt, cfg, args=None, silent=False):
    silent or print(f"Connecting to {fgt['ip']} with {cfg['fgt_user']} / {cfg['fgt_password']}")
    client.connect(
        fgt['ip'],
        port = fgt.get('port', 22),
        username = cfg['fgt_user'],
        password = cfg['fgt_password']
    )
    interact = SSHClientInteraction(client, display=(not silent))
    silent or print('>')
    interact.expect('.*# ')
    interact.send('execute factoryreset2 keepvmlicense')
    interact.expect(r'.*\(y/n\)')
    interact.send('y')
    interact.expect('.*')       
    silent or print('<')
    return True

def __applyCLIConfig(client, fgt, cfg, cli_config, silent=False):
    silent or print(f"Connecting to {fgt['ip']} with {cfg['fgt_user']} / {cfg['fgt_password']}")
    client.connect(
        fgt['ip'],
        port = fgt.get('port', 22),
        username = cfg['fgt_user'],
        password = cfg['fgt_password'],
        timeout = 10
    )    
    stdin, stdout, stderr = client.exec_command(cli_config)

    output = []
    while True:
        line = stdout.readline()
        if not line: break
        # Handle '\r' for long outputs with "--More--"
        output.append(line[line.rfind('\r')+1:])

    return output    

def __getNewmanCommand(cfg, session, vars={}, silent=False):
    command = []
    command.append('newman run')
    command.append('"' + cfg['postman_collection'] + '"')
    command.append('--insecure')
    command.append('--env-var "ip=' + cfg['fmg_host'] + '"')
    command.append('--env-var "username=' + cfg['fmg_user'] + '"')
    command.append('--env-var "password=' + cfg['fmg_password'] + '"')
    command.append('--env-var "adom=' + cfg['fmg_adom'] + '"')
    command.append('--env-var "session=' + session.getSessionCookie() + '"')
    for k,v in vars.items(): command.append('--env-var "' + k + '=' + str(v) + '"')
    if session.verbose: command.append('--verbose')
    if silent: command.append('--silent')
    return command      

def __monitorZTP(session, dev_list, min_taskid, silent=False):
    ztp_status = { d: None for d in dev_list }
    ztp_tasks, tid_completed = [], []
    found_tasks, completed, fail, retries = 0, 0, 0, 15
    lastid = min_taskid

    silent or print("Preparing to start ZTP monitoring...")
    while retries and completed < len(dev_list):
        silent or print(f"Waiting... (retries left: {retries})")
        sleep(40)

        # Look for new ZTP tasks
        if found_tasks < len(dev_list):
            new_tasks = session.getLastTasks()
            maxid = new_tasks[0]['id']
            if maxid > lastid:
                if maxid > lastid + 1:
                    # More than one new task detected, get them all
                    new_tasks = session.getLastTasks(
                        count = maxid - lastid
                    )
                ztp_tasks.extend(
                    [ t['id'] for t in new_tasks if t['title'] == 'autolinktitle' ]
                )
                lastid = maxid

        # Check ZTP tasks status
        for tid in ztp_tasks:
            task = session.getTask(tid, detailed=True)

            if not ztp_status[task['dev_name']]:
                # New ZTP task found
                found_tasks += 1
            ztp_status[task['dev_name']] = task

            if task['completed']:
                completed += 1
                tid_completed.append(tid)
                if not task['success']: fail += 1
        
        # Stop monitoring completed ZTP tasks
        ztp_tasks = [ tid for tid in ztp_tasks if tid not in tid_completed ]
        
        silent or print()
        silent or print_table(
            ztp_status,
            columns={
                'Completed': 'completed',
                'Success': 'success',
                'Last Message': "message"
            },
            keyColumn="Device",
            title="Current ZTP Status" 
        )
        retries -= 1
        silent or print(f"SUMMARY: {found_tasks} ZTP TaskIDs Found, \033[32m\033[1m{completed} Completed\033[0m, \033[91m\033[1m{fail} Failed\033[0m.")
        silent or print()

    if completed < len(dev_list):
        raise Exception("ZTP process did not complete for some of the devices!")

    return fail, ztp_status.values()


