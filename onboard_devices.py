#!/usr/bin/env python3

import sys
from orch_base import *

def main():
  if (len(sys.argv) != 2):
    print(f"\033[91m\033[1mERROR:\033[0m Please specify the inventory CSV file!") 
    exit(1)
  cfg = readConfig()
  task = {
    'src': sys.argv[1]
  }
  onboardDevicesTask(cfg, task)


if __name__ == "__main__":
    main()    