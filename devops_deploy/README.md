# Devops deploy prototype

Use this script to quickly deploy a "skeleton" devops environemnt.

## What the script does:
* Creates a devops BU
* Crates all of the projects layed out in the overview diagram
* Creates all of the instances needed in the environemnt
* Deploys a Jenkins and Gitlab App stack in the pipeline project.

## What the script does not do:
* Configure the environemnt
* Configure the Gitlab or Jenkins App stacks
* Build an actual dev pipline.

## How to run
1. Download the RC file and the keyfile form Zerostack
2. Once you have them make the neccessary mods to the the RC file add the variable OS_REGION.
3. Source the RC file
4. use python to run the deploy.py script and answer the questions when prompted.

### Ex. RC file for cloud admin

USER_NAME=adminuser

USER_PASSWD=P@ssw0rd

USER_DOMAIN=admin.local

PROJECT_DOMAIN=admin.local

USER_PROJECT=zs_default

USER_REGION='Morrisville'

ZS_CERT_FILE=/home/builder/keys/morrisville/zs_Certificate_ca.bundle
export OS_AUTH_URL=https://console.zerostack.com/os/d89afe93-7355-4660-ad02-724db405e4f4/regions/73657ac1-8a38-4968-a912-f833de58f44d/keystone/v3

export OS_CACERT=$ZS_CERT_FILE

export OS_IDENTITY_API_VERSION=3

export OS_IMAGE_API_VERSION=1

export OS_VOLUME_API_VERSION=2

export OS_USERNAME=$USER_NAME

export OS_USER_DOMAIN_NAME=$USER_DOMAIN

export OS_PASSWORD=$USER_PASSWD

export OS_PROJECT_NAME=$USER_PROJECT

export OS_PROJECT_DOMAIN_NAME=$PROJECT_DOMAIN

export OS_REGION='Morrisville'

NOTE: This is a beta and has only been tested with a cloud admin account. This is a very flat script with no bells and whistles.
