#!/bin/bash

mkdir -p solution-deployer solution-deployer/fmg_api
cp *.py install.sh solution-deployer
cp fmg_api/* solution-deployer/fmg_api
tar cfz solution-deployer.tgz solution-deployer/*
rm -rf solution-deployer

