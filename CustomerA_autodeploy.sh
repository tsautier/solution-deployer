#!/bin/bash

start=`date +%s`

echo ------------------------------------------------------------------------
echo Downloading the latest version of the Jinja Templates for release/7.2...
echo ------------------------------------------------------------------------
mkdir -p tenants/shared
wget -O tenants/shared/7.2.zip https://github.com/fortinet-solutions-cse/sdwan-advpn-reference/archive/refs/heads/release/7.2.zip
unzip -o tenants/shared/7.2.zip 'sdwan-advpn-reference-release-7.2/bgp-on-loopback/*.j2' -d tenants/shared/

echo
echo -----------------------------------------------------------------------------
echo Downloading the latest version of the Postman collection for CSE-SDWAN-72x...
echo -----------------------------------------------------------------------------
wget -O tenants/shared/Managed_SDWAN_7_2_x.postman.json https://raw.githubusercontent.com/fortinet-solutions-cse/postman_collections/7.2.x/Managed_SDWAN_7_2_x.postman.json 

echo
echo ---------------------------
echo Copying Project Template...
echo ---------------------------
unzip -o -j ../projects.zip 'projects/CustomerA/Project.j2' -d tenants/CustomerA

echo
echo ------------------------------
echo Generating device inventory...
echo ------------------------------
./generate_inventory.py | grep -A 7 "inventory.CustomerA.csv" | tail -n +3 > tenants/CustomerA/inventory.CustomerA.csv
cat tenants/CustomerA/inventory.CustomerA.csv

echo
echo ---------------------------------------
echo Starting the Fancy Solution Deployer...
echo ---------------------------------------
ORCH_TENANT=CustomerA ./autodeploy.py

end=`date +%s`
min=$((($end-$start)/60))
sec=$((($end-$start)%60))
echo Running time: $min minutes, $sec seconds