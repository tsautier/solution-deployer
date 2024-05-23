#!/bin/bash

if [ $# -ne 1 ]; then echo Please specify the target directory.; exit 1; fi
dst_dir="$1"
src_dir=`dirname $0`

echo ----------------------------------------------------------
echo Copying the Solution Deployer into the target directory...
echo ----------------------------------------------------------

mkdir -p $dst_dir
cp $src_dir/*.py $dst_dir

mkdir -p $dst_dir/fmg_api
cp $src_dir/fmg_api/*.py $dst_dir/fmg_api

mkdir -p $dst_dir/tenants