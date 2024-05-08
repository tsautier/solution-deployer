#!/bin/bash

if [ $# -ne 1 ]; then echo Please specify the target directory.; exit 1; fi
dir="$1"

echo ----------------------------------------------------------
echo Copying the Solution Deployer into the target directory...
echo ----------------------------------------------------------

mkdir -p $dir
cp *.py $dir
cp *.sh $dir 

mkdir -p $dir/fmg_api
cp fmg_api/*.py $dir/fmg_api

mkdir -p $dir/tenants