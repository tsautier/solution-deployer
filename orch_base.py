#!/usr/bin/env python3

from yaml import safe_load
from os import environ
from fmg_api.api_base import ApiSession

def readConfig():

    print("========================")
    print(" Tenant: " + environ.get("ORCH_TENANT"))
    print("========================")
    tenantdir = "tenants/" + environ.get("ORCH_TENANT")

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
