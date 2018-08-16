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

NOTE: This is a beta and has only been tested with a cloud admin account. This is a very flat script with no bells and whistles.
