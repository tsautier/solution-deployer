#!/bin/bash

status_fail=0

# Configure external NAT
./configure_ext_nat.py || status_fail=1

# Finalize FGT configuration
./configure_devices.py || status_fail=1

sleep 5

# Update public IPs in Postman variables (CustomerU)
./update_postman_vars.py || status_fail=1

exit $status_fail
