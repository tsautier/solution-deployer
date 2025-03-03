#!/usr/bin/env python3

# autodeploy.py                                                              #
# Solution Deployer, Version 7.6.x b120                                      #
# -------------------------------------------------------------------------- #
# Maintainers: CSE Telco/MSSP EMEA, Fortinet (internal use only)             #
# -------------------------------------------------------------------------- #

import argparse
from orch_base import *

def main():

    # Config from config.yaml
    cfg = readConfig()
    session = getApiSession(cfg)

    # Command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--tags', metavar="TAG1,TAG2,...",
        help='tags to execute (comma-delimited)',
        type=lambda s: [t for t in s.split(',')],
        default=cfg.get('default_tags', None)
    )
    parser.add_argument(
        '--skip-tags', metavar="TAG1,TAG2,...",
        help='tags to skip (comma-delimited)',
        type=lambda s: [t for t in s.split(',')],
        default=cfg.get('default_skip_tags', None)
    )
    args = parser.parse_args()
   
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

        if (args.tags and task.get('tag', '') not in args.tags) or \
           (args.skip_tags and not args.tags and task.get('tag', '') in args.skip_tags):
            print("\033[35mSKIPPED by tag\033[0m")
            continue

        try:
            if task['type'] == 'postman':
                runPostmanTask(cfg, session, task)
            elif task['type'] == 'cli_templates':
                importCLITemplateTask(session, task)
            elif task['type'] == 'delete_devices':
                deleteDevicesTask(session, task)
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