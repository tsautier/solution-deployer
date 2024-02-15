#!/usr/bin/env python3

from orch_base import runCLICommandTask, applyCLIConfigTask
from yaml import safe_load

def main():
    
    with open('tenants/shared/config.yaml', 'r') as cfgfile:
        cfg = safe_load(cfgfile)

    task = {
        'site': 'zz_ext',
        'cli': 'diagnose ip address list'
    }
    output = runCLICommandTask(cfg, task)

    vars = {}
    for str in output:
        params = [ v.rstrip() for v in str.split(' ') if '=' in v ]
        intf = { p.split('=')[0]: p.split('=')[1] for p in params }
        if intf: vars[intf['devname']] = intf['IP'].split('->')[0]
    
    task = {
        'src': 'tenants/shared/zz_ext.j2',
        'vars': vars
    }
    applyCLIConfigTask(cfg, task)

if __name__ == "__main__":
    main()    