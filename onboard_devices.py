#!/usr/bin/env python3

import sys
from orch_base import *

def main():
  if (len(sys.argv) != 3):
    print(f"\033[91m\033[1mERROR:\033[0m Please specify either 'src <file>' for the inventory CSV file or 'site <name>' for a single site!") 
    exit(1)
  cfg = readConfig()
  task = {
    sys.argv[1]: sys.argv[2]
  }
  onboardDevicesTask(cfg, task)


if __name__ == "__main__":
    main()    