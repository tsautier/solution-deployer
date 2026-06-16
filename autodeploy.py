#!/usr/bin/env python3

# autodeploy.py                                                              #
# Solution Deployer, Version 7.6.x                                           #
# -------------------------------------------------------------------------- #
# Maintainers: CSE Telco/MSSP EMEA, Fortinet (internal use only)             #
# -------------------------------------------------------------------------- #

import argparse
from orch_base import *

DEPLOYER_VER = "7.6.x b171"

def main():

    print(f"Solution Deployer, Version {DEPLOYER_VER}")

    # Config from config.yaml
    cfg = readConfig()

    # Command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--tags', metavar="TAG1,TAG2,...",
        help='tags to execute (comma-delimited)',
        type=lambda s: [t for t in s.split(',')]
    )
    parser.add_argument(
        '--skip-tags', metavar="TAG1,TAG2,...",
        help='tags to skip (comma-delimited)',
        type=lambda s: [t for t in s.split(',')]
    )
    parser.add_argument(
        '--tasks', metavar="NAME1,NAME2,...",
        help='specific tasks to execute (by name, comma-delimited)',
        type=lambda s: [t for t in s.split(',')]
    )
    parser.add_argument(
        '--dry',
        action='store_true',
        help='dry run (test tags)'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='more verbose output'
    )    
    args = parser.parse_args()
    if args.tasks and (args.tags or args.skip_tags):
        parser.error("filter tasks either by name (--tasks) or by tags (--tags, --skip-tags), but not both!")

    session = getApiSession(cfg)
   
    print()
    if args.dry: print("Dry-run mode ON.")
    if args.verbose: 
        print("Verbose mode ON.")
        session.verbose = True

    print("Running automated deployment sequence...")

    success, fail = 0, 0
    for i, task in enumerate(cfg['tasks'], start=1):
        if fail and cfg.get('halt_on_fail', True):
            print(f"\033[91m\033[1mHALT ON FAIL:\033[0m Halting here, because the previous task has failed!") 
            break
        print()
        print(f"TASK {i}: {task['name']}")
        print("---------------------------------------------------")

        # Running specific tasks (by name)
        if args.tasks and task['name'] not in args.tasks:
            print("\033[35mSKIPPED by name\033[0m")
            continue            

        # Running specific tasks (by tags)
        if not args.tasks:
            # Consider default values for tags and skip_tags
            args.tags = args.tags or cfg.get('default_tags')
            args.skip_tags = args.skip_tags or cfg.get('default_skip_tags')

            # A task can have zero or more tags (comma-delimited)
            task_tags = task.get('tag', '').split(',')
            if args.tags and args.skip_tags:
                args.skip_tags = [ t for t in args.skip_tags if t not in args.tags ]
            if (args.tags and not any(tag in args.tags for tag in task_tags)) or \
            (args.skip_tags and any(tag in args.skip_tags for tag in task_tags)):
                print("\033[35mSKIPPED by tag\033[0m")
                continue

        if args.dry: continue

        try:
            if task['type'] == 'postman':
                runPostmanTask(cfg, session, task)
            elif task['type'] == 'cli_templates':
                importCLITemplateTask(session, task)
            elif task['type'] == 'delete_devices':
                deleteDevicesTask(session, task)
            elif task['type'] == 'model_devices':
                createModelDevicesTask(session, task)
            elif task['type'] == 'apply_cli':
                applyCLIConfigTask(cfg, task)
            elif task['type'] == 'onboard':
                if fail:
                    raise Exception("Skipping the onboarding, because (some of) the previous tasks failed!")
                onboardDevicesTask(cfg, task, session)
            success += 1
            print()
            print(f"\033[32m\033[1mTASK {i} SUCCEEDED.\033[0m")
        except Exception as e:
            fail += 1
            print()
            print(f"\033[91m\033[1mTASK {i} FAILED:\033[0m {e}") 

    print()
    print(f"All done! \033[32mSuccess: {success}\033[0m, \033[91mFail: {fail}\033[0m")


if __name__ == "__main__":
    main()    