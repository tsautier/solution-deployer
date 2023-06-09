#!/usr/bin/env python3

import csv, io
from yaml import safe_load
from paramiko import SSHClient, AutoAddPolicy, ssh_exception
from contextlib import redirect_stdout
from orch_base import *

def __doGetSN(client, fgt, cfg):
    client.connect(
        fgt['ip'],
        port = fgt.get('port', 22),
        username = cfg['fgt_user'],
        password = cfg['fgt_password']
    )
    stdin, stdout, stderr = client.exec_command('get system status')
    return next(l.split(': ')[1].strip() for l in stdout.readlines() if ("Serial-Number" in l))

def getSN(fgt_name, cfg):
    fgt = cfg['sites'][fgt_name]
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())

    try:
        sn = __doGetSN(client, fgt, cfg)
    except ssh_exception.AuthenticationException as e:
        with (redirect_stdout(io.StringIO())):
            setNewPassword(client, fgt, cfg)
        sn = __doGetSN(client, fgt, cfg)
    finally:
        client.close()

    return sn


def printInventory(cfg, in_file):
    with open(in_file, 'r', encoding='utf-8-sig') as f, io.StringIO() as s:
        csvIn = csv.DictReader(f)
        csvOut = csv.DictWriter(s, csvIn.fieldnames)
        csvOut.writeheader()
        for d in csvIn:
            d['sn'] = getSN(d['name'], cfg)
            csvOut.writerow(d)
        print(s.getvalue())


def main():

    tenantdir = "tenants/CustomerA"
    with open(tenantdir + '/config.yaml', 'r') as cfgfile:
        cfg = safe_load(cfgfile)
        print()
        print("inventory.CustomerA.csv")
        print("=======================")            
        printInventory(cfg, tenantdir + '/inventory.CustomerA.j2')

    tenantdir = "tenants/CustomerB"
    with open(tenantdir + '/config.yaml', 'r') as cfgfile:
        cfg = safe_load(cfgfile)
        print()
        print("inventory.CustomerB.csv")
        print("=======================")            
        printInventory(cfg, tenantdir + '/inventory.CustomerB.j2')



if __name__ == "__main__":
    main()
