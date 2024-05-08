# configure_ext_nat.py                                                       #
# Solution Deployer, Version 7.4.x b100                                      #
# -------------------------------------------------------------------------- #
# Maintainers: CSE Telco/MSSP EMEA, Fortinet (internal use only)             #
# -------------------------------------------------------------------------- #

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
        if intf: 
            ip = intf['IP'].split('->')[0]
            gw = ip.rsplit('.', 1)[0]+'.1'
            vars[intf['devname']] = ip
            vars[intf['devname']+'_gw'] = gw
    
    task = {
        'src': 'tenants/shared/zz_ext.j2',
        'vars': vars
    }
    applyCLIConfigTask(cfg, task)

if __name__ == "__main__":
    main()    