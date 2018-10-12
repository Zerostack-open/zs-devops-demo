#!/bin/bash

if [ -f '/etc/redhat-release' ]; then
	yum install -y epel-release
	yum install -y git
	yum install -y python-setuptools python-setuptools-devel
	easy_install pip

	pip install --upgrade ansible 2>&1
else
	apt-get update -y
	apt-get install software-properties-common -y
	apt-add-repository ppa:ansible/ansible -y
	apt-get update -y
	apt-get install ansible -y
fi
