# Devops deploy prototype
<br />
Use this script to quickly deploy a "skeleton" devops environemnt.
<br />
## What the script does:
1. Creates a devops BU <br />
2. Crates all of the projects layed out in the overview diagram <br />
3. Creates all of the instances needed in the environemnt <br />
4. Deploys a Jenkins and Gitlab App stack in the pipeline project <br />

## What the script does not do:
1. Configure the environemnt <br />
2. Configure the Gitlab or Jenkins App stacks <br />
3. Build an actual dev pipline <br />

## How to run
1. Download the RC file and the keyfile form Zerostack
2. Once you have them make the neccessary mods to the the RC file add the variable OS_REGION.
3. Source the RC file
4. use python to run the deploy.py script and answer the questions when prompted.

NOTE: This is a beta and has only been tested with a cloud admin account. This is a very flat script with no bells and whistles.
