# Devops deploy prototype

Use this script to quickly deploy a "skeleton" devops environemnt.

## What the script does:
1. Creates a devops BU 
2. Crates all of the projects layed out in the overview diagram
3. Creates all of the instances needed in the environemnt
4. Deploys a Jenkins and Gitlab App stack in the pipeline project

## What the script does not do:
1. Configure the environemnt <br />
2. Configure the Gitlab or Jenkins App stacks <br />
3. Build an actual dev pipline <br />

## How to run
1. Download the RC file and the keyfile form Zerostack
2. Once you have them make the neccessary mods to the the RC file add the variable OS_REGION.
3. Source the RC file
4. use python to run the deploy.py script and answer the questions when prompted.

### Ex. RC file for cloud admin

USER_NAME=adminuser <br />
USER_PASSWD=mypass <br />
USER_DOMAIN=admin.local <br />
PROJECT_DOMAIN=admin.local <br />
USER_PROJECT=zs_default <br />
USER_REGION='BestRegion' <br />
ZS_CERT_FILE=~/zs_Certificate_ca.bundle <br />
export OS_AUTH_URL=https://console.zerostack.com/os/d99afe93-7355-4660-ad02-724db405e4f4/regions/73678ac1-8a38-4968-a912-f833de58f44d/keystone/v3 <br />
export OS_CACERT=$ZS_CERT_FILE <br />
export OS_IDENTITY_API_VERSION=3 <br />
export OS_IMAGE_API_VERSION=1 <br />
export OS_VOLUME_API_VERSION=2 <br />
export OS_USERNAME=$USER_NAME <br />
export OS_USER_DOMAIN_NAME=$USER_DOMAIN <br />
export OS_PASSWORD=$USER_PASSWD <br />
export OS_PROJECT_NAME=$USER_PROJECT <br />
export OS_PROJECT_DOMAIN_NAME=$PROJECT_DOMAIN <br />
export OS_REGION='BestRegion' <br />
<br />
NOTE: This is a beta and has only been tested with a cloud admin account. This is a very flat script with no bells and whistles.
