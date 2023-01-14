#!/usr/bin/env python3

import csv, io
from yaml import safe_load
from paramiko import SSHClient, AutoAddPolicy
from orch_base import *

def getSN(fgt, fgt_user, fgt_password):
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    client.connect(
        fgt['ip'],
        port = fgt.get('port', 22),
        username = fgt_user,
        password = fgt_password
    )
    stdin, stdout, stderr = client.exec_command('get system status')
    sn = next(l.split(': ')[1].strip() for l in stdout.readlines() if ("Serial-Number" in l))
    client.close()
    return sn

def printInventory(cfg, in_file):
    with open(in_file, 'r', encoding='utf-8-sig') as f, io.StringIO() as s:
        csvIn = csv.DictReader(f)
        csvOut = csv.DictWriter(s, csvIn.fieldnames)
        csvOut.writeheader()
        for d in csvIn:
            d['sn'] = getSN(cfg['sites'][d['name']], cfg['fgt_user'], cfg['fgt_password'])
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
