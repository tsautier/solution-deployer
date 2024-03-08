#!/bin/bash

start=`date +%s`

echo ------------------------------------------------------------------------
echo Downloading the latest version of the Jinja Templates for release/7.2...
echo ------------------------------------------------------------------------
mkdir -p tenants/shared
wget -O tenants/shared/7.2.zip https://github.com/fortinet-solutions-cse/sdwan-advpn-reference/archive/refs/heads/release/7.2.zip
unzip -o tenants/shared/7.2.zip 'sdwan-advpn-reference-release-7.2/bgp-on-loopback/*.j2' -d tenants/shared/

echo
echo -----------------------------------------------------------------------------------------
echo Downloading the latest version of the Postman collection for MSSP Deployment Guide 7.2...
echo -----------------------------------------------------------------------------------------
wget -O tenants/shared/Deployment_Guide_SDWAN_7_2_x.postman.json https://raw.githubusercontent.com/fortinet-solutions-cse/postman_collections/7.2.x/Deployment_Guide_SDWAN_7_2_x.postman.json

echo
echo ------------------------------
echo Generating device inventory...
echo ------------------------------
./generate_inventory.py | grep -A 9 "inventory.CustomerC.csv" | tail -n +3 > tenants/CustomerC/inventory.CustomerC.csv
cat tenants/CustomerC/inventory.CustomerC.csv

echo
echo ---------------------------------------
echo Starting the Fancy Solution Deployer...
echo ---------------------------------------
ORCH_TENANT=CustomerC ./autodeploy.py

end=`date +%s`
min=$((($end-$start)/60))
sec=$((($end-$start)%60))
echo Running time: $min minutes, $sec seconds