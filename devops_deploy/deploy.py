import __future__
import os
import sys
import requests
import shutil
import subprocess
import json
import pprint
import urllib3
import time
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

zsbuname = raw_input("Please enter a Business Unit name: ")
username = raw_input("Please enter a Business Unit Admin name: ")
password = raw_input("Please enter the admin password, CAUTION: This is in plain text: ")
email = raw_input("Please enter the BU admin email: ")
#imagename = raw_input("Please enter a valid OS image name from your image library: ")

auth_username = os.getenv('OS_USERNAME',None)
auth_password = os.getenv('OS_PASSWORD',None)
auth_url = os.getenv('OS_AUTH_URL',None)
project_name = os.getenv('OS_PROJECT_NAME',None)
user_domain_name = os.getenv('OS_USER_DOMAIN_NAME',None)
project_domain_name = os.getenv('OS_PROJECT_DOMAIN_NAME',None)
cacert = os.getenv('OS_CACERT',None)
user_region = os.getenv('OS_REGION',None)

if(auth_username == None or auth_password == None or auth_url == None or \
   project_name == None or user_region == None or user_domain_name == None or \
   project_domain_name == None or cacert == None):
    print "Export the Zerostack RC file, or explicitly define authentication environment variables."
    sys.exit(1)

if(user_region == None):
    print "Add user region variable OS_REGION to the Zerostack rc file and re-export, or export OS_REGION as an environment variable."
    sys.exit(1)

#get the region ID
regionsplit = auth_url.split('/')
region_id = regionsplit[6]

#get the base url
baseurl = auth_url[:-12]

#get the login token
try:
    body = '{"auth":{"identity":{"methods":["password"],"password":{"user":{"domain":{"name":"%s"},"name":"%s","password":"%s"}}},"scope":{"domain":{"name":"%s"}}}}' \
           %(project_domain_name,auth_username,auth_password,project_domain_name)
    #headers={"content-type":"application/json"}
    token_url = auth_url+'/auth/tokens'
    trequest = requests.post(token_url,verify = False,data = body,headers={"content-type":"application/json"})
    jtoken = json.loads(trequest.text)
    admin_user_id = jtoken['token']['user']['id']
    token = trequest.headers.get('X-Subject-Token')
except Exception as e:
    print e
    sys.exit(1)

print "Looking for the default image"
image_id = None
try:
    send_url = baseurl + '/glance/v2/images?visibility=public'
    r = requests.get(send_url,verify = False,headers={"content-type":"application/json","X-Auth-Token":token})
    images = json.loads(r.text)
    count = 0
    im = []
    for image in images['images']:
        im.append({'count':count,'imagename':image['name'],'imageid':image['id']})
        count += 1
except Exception as e:
    print e
    sys.exit(1)

for i in im:
    print "ID: %s   Name: %s"%(i['count'],i['imagename'])

try:
    imid = raw_input('Enter the ID of the image to use: ')
    for i in im:
        if(i['count'] == int(imid)):
            image_id = i['imageid']
            break
except Exception as e:
    print e
    sys.exit(1)


#Create a new BU
domain_id = None
print "\n\nCreating business unit: %s"%(zsbuname)
try:
    send_url = auth_url + '/domains'
    data = '{"domain":{"name":"%s","description":"BU created on by %s.","ldapSet":false}}'%(zsbuname,auth_username)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
    if(r.status_code == 409):
        print "BU %s already exists."%(zsbuname)
        sys.exit(1)
    j = json.loads(r.text)
    #get the domain id
    domain_id = j['domain']['id']
except Exception as e:
    print e
    sys.exit(1)
print "%s business unit has been created, ID: %s.\n\n"%(zsbuname,domain_id)

#get the roles and find the Admin role ID
admin_id = None
print "Gathering the available roles."
try:
    send_url = auth_url + '/roles'
    r = requests.get(send_url,verify = False,headers={"content-type":"application/json","X-Auth-Token":token})
    j = json.loads(r.text)
    for role in j['roles']:
        if(role['name'] == 'admin'):
            admin_id = role['id']
except Exception as e:
    print e
    sys.exit(1)
print "Found the admin role ID: %s\n\n"%(admin_id)


#Create a BU admin
print "Creating the BU Admin account for %s."%(username)
user_id = None
try:
    send_url = auth_url + '/users'
    data = '{"user":{"email":"%s","enabled":true,"name":"%s","domain_id":"%s","password":"%s"}}'%(email,username,domain_id,password)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
    j = json.loads(r.text)
    user_id = j['user']['id']
except Exception as e:
    print e
    sys.exit(1)
print "Created BU Admin with ID: %s.\n\n"%(user_id)

#createing the control project
print "Creating the Devops BU %s control project."%(zsbuname)
project_id = None
try:
    send_url = 'https://console.zerostack.com/v2/clusters/%s/projects'%(region_id)
    data = '{"description":"DevOps Control Project for %s devops BU.","domain_id":"%s","name":"DvOps Control","finite_duration":false,\
           "metadata":{"templateId":"Large","custom_template":"true"},\
           "quota":{"compute_quota":{"cores":128,"floating_ips":64,"injected_file_content_bytes":-1,"injected_file_path_bytes":-1,"injected_files":-1,"instances":64,"key_pairs":-1,"metadata_items":-1,"ram":262144},\
           "storage_quota":{"backup_gigabytes":-1,"backups":-1,"snapshots":640,"volumes":640,"gigabytes":25600},\
           "network_quota":{"subnet":-1,"router":20,"port":-1,"network":64,"floatingip":64,"vip":-1,"pool":-1}}}'%(zsbuname,domain_id)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
    j = json.loads(r.text)
    project_id = j['id']
except Exception as e:
    print e
    sys.exit(1)
print "Created devops control project with ID: %s\n\n"%(project_id)

#add the admin
print "Adding the admin account to the devops control project."
try:
    send_url = auth_url + '/projects/%s/users/%s/roles/%s'%(project_id,user_id,admin_id)
    r = requests.put(send_url,verify = False,headers={"content-type":"application/json","X-Auth-Token":token})
except Exception as e:
    print e
    sys.exit(1)
print "Admin user added.\n\n"

#add the basic security group
print "Creating a basic Security group for %s BU."%(zsbuname)
secgroup_id = None
try:
    send_url = baseurl + '/neutron/v2.0/security-groups'
    data = '{"security_group":{"name":"Basic","description":"security group Basic","tenant_id":"%s"}}'%(project_id)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
    j = json.loads(r.text)
    secgroup_id = j['security_group']['id']
except Exception as e:
    print e
    sys.exit(1)
print "Created the basic security group with ID: %s.\n\n"%(j['security_group']['id'])

#add the ports to the security group
ports = [{'icmp':'null'},{'tcp':'22'},{'tcp':'80'},{'tcp':'443'},{'tcp':'8443'}]
for port in ports:
    try:
        send_url = baseurl + '/neutron/v2.0/security-group-rules'
        data = '{"security_group_rule":{"direction":"ingress","port_range_min":%s,"ethertype":"IPv4","port_range_max":%s,"protocol":"%s","security_group_id":"%s","tenant_id":"%s"}}'%(port.values()[0],port.values()[0],port.keys()[0],secgroup_id,project_id)
        r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
        j = json.loads(r.text.encode('latin-1'))
    except Exception as e:
        print e
        sys.exit(1)
    print "Created the basic security group rule, ID: %s.\n\n"%(j['security_group_rule']['id'])


print "Creating a project scoped token for %s."%(username)
project_token = None
try:
    send_url = auth_url+"/auth/tokens"
    data = '{"auth":{"scope":{"project":{"id":"%s"}},"identity":{"methods":["token"],"token":{"id":"%s"}}}}'%(project_id,token)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
    project_token = r.headers.get('X-Subject-Token')
except Exception as e:
    print e
    sys.exit(1)
print "Created project token key: %s.\n\n"%(project_token)


#Build the defult sec key
print "Creating default security keys, devops_keypair, for devops project in the %s BU."%(zsbuname)
devops_key = "%s_devops_keypair"%(zsbuname)
try:
    send_url = baseurl+"/nova/v2/%s/os-keypairs"%(project_id)
    data = '{"keypair":{"name":"%s_devops_keypair"}}'%(zsbuname)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":project_token})
    keyinfo = json.loads(r.text.encode('latin-1'))
except Exception as e:
    print e
    sys.exit(1)
print "Created the security key devops_keypair.\n\n"

time.sleep(2)
keypair = keyinfo['keypair']

#updateing the control project
print "Updateing the Devops BU %s control project."%(zsbuname)
try:
   send_url = 'https://console.zerostack.com/v2/clusters/%s/projects/%s'%(region_id,project_id)
   data = '{"description":"DevOps Control Project for %s devops BU.","domain_id":"%s","name":"DvOps Control","finite_duration":false,\
          "metadata":{"templateId":"Large","custom_template":"true","userName":"%s","user_id":"%s","fingerprint":"%s","keypairName":"%s","private_key":%s,"public_key":"%s"},\
          "quota":{"compute_quota":{"cores":128,"floating_ips":64,"injected_file_content_bytes":-1,"injected_file_path_bytes":-1,"injected_files":-1,"instances":64,"key_pairs":-1,"metadata_items":-1,"ram":262144},\
          "storage_quota":{"backup_gigabytes":-1,"backups":-1,"snapshots":640,"volumes":640,"gigabytes":25600},\
          "network_quota":{"subnet":-1,"router":20,"port":-1,"network":64,"floatingip":64,"vip":-1,"pool":-1}}}'%(zsbuname,domain_id,auth_username,admin_user_id,keypair['fingerprint'],keypair['name'],json.dumps(keypair['private_key']),keypair['public_key'])
   r = requests.patch(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
   j = json.loads(r.text)
   project_id = j['id']
except Exception as e:
    print e
    sys.exit(1)
print "Updated devops control project with ID: %s\n\n"%(project_id)

print "Creating the devops network in DevOps project."
network_id = None
subnet_id = None
try:
    send_url = 'https://console.zerostack.com/v2/clusters/%s/networks'%(region_id)
    data = '{"admin_state_up":true,"name":"DevOps-network","subnets":[{"name":"Subnet1","enable_dhcp":true,"gateway_ip":"10.10.10.1","ip_version":4,"cidr":"10.10.10.0/24","allocation_pools":[{"start":"10.10.10.2","end":"10.10.10.254"}],"dns_nameservers":["8.8.8.8"],"tenant_id":"%s"}],"tenant_id":"%s","visibility":"buShared","visibility_scope":[{"domain_id":"%s"}],"project_id":"%s"}'%(project_id,project_id,region_id,project_id)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":project_token})
    j = json.loads(r.text)
    network_id = j['id']
    subnet_id = j['subnet_details'][0]['id']
except Exception as e:
    print e
    sys.exit(1)
print "Created the DevOps default network, ID: %s.\n\n"%(network_id)

#list the available external networks
ext_net_id = None
try:
    send_url = 'https://console.zerostack.com/v2/clusters/%s/networks/?visibility=public&domain_id=%s&project_id=%s'%(region_id,domain_id,project_id)
    r = requests.get(send_url,verify = False,headers={"content-type":"application/json","X-Auth-Token":token})
    nets = json.loads(r.text)
    for net in nets:
        if(net['provider:physical_network'] == 'external' and net['router:external'] == True and net['shared'] == True):
            ext_net_id = net['id']
except Exception as e:
    print e
    sys.exit(1)
print "Found external network with id: %s."%(ext_net_id)

#add the basic security group
print "Creating a router for DevOps network."
router_id = None
try:
    send_url = baseurl + '/neutron/v2.0/routers'
    data = '{"router":{"name":"DevOpsNet-Router","external_gateway_info":{"network_id":"%s"},"tenant_id":"%s"}}'%(ext_net_id,project_id)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":project_token})
    j = json.loads(r.text)
    router_id = j['router']['id']
except Exception as e:
    print e
    sys.exit(1)
print "Created the the default router.\n\n"

#add the router interface to the network subnet
print "Adding interface to router interface"
try:
    send_url = baseurl + '/neutron/v2.0/routers/%s/add_router_interface'%(router_id)
    data = '{"subnet_id":"%s"}'%(subnet_id)
    r = requests.put(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":project_token})
    j = json.loads(r.text)
except Exception as e:
    print e
    sys.exit(1)
print "Added network interface to the router, interface ID: %s\n\n"%(j['id'])

#add router gateway interface
print "Adding gateway interface to router."
try:
    send_url = baseurl + '/neutron/v2.0/routers/%s'%(router_id)
    data = '{"router":{"name":"DevOpsNet-Router","external_gateway_info":{"network_id":"%s"},"admin_state_up":true}}'%(ext_net_id)
    r = requests.put(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":project_token})
    j = json.loads(r.text)
except Exception as e:
    print e
    sys.exit(1)
print "Added the gateway interface to the router, ID: %s, External IP: %s.\n\n"%(j['router']['id'],j['router']['external_gateway_info']['external_fixed_ips'][0]['ip_address'])


print "Updateing the network."
try:
    send_url = 'https://console.zerostack.com/v2/clusters/%s/networks/%s'%(region_id,network_id)
    data = '{"name":"DevOps-network","router:external":false,"admin_state_up":true,"subnets":[{"id":"%s"}],"visibility":"buShared","visibility_scope":[{"domain_id":"%s"}]}'%(subnet_id,domain_id)
    r = requests.put(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":project_token})
    j = json.loads(r.text)
except Exception as e:
    print e
    sys.exit(1)
print "Updated the DevOps default network, ID: %s.\n\n"%(network_id)

control_vms = [
   {'vm':'Ansible Control','code':'IyEvYmluL2Jhc2gKCmlmIFsgLWYgJy9ldGMvcmVkaGF0LXJlbGVhc2UnIF07IHRoZW4KCXl1bSBpbnN0YWxsIC15IGVwZWwtcmVsZWFzZQoJeXVtIGluc3RhbGwgLXkgZ2l0Cgl5dW0gaW5zdGFsbCAteSBlYXN5X2luc3RhbGwKCgllYXN5X2luc3RhbGwgcGlwCgoJcGlwIGluc3RhbGwgLS11cGdyYWRlIGFuc2libGUgMj4mMQplbHNlCglhcHQtZ2V0IHVwZGF0ZSAteQoJYXB0LWdldCBpbnN0YWxsIHNvZnR3YXJlLXByb3BlcnRpZXMtY29tbW9uIC15CglhcHQtYWRkLXJlcG9zaXRvcnkgcHBhOmFuc2libGUvYW5zaWJsZSAteQoJYXB0LWdldCB1cGRhdGUgLXkKCWFwdC1nZXQgaW5zdGFsbCBhbnNpYmxlIC15CmZp'},
   {'vm':'OpenShift Control','code':None},
   {'vm':'Cloudforms','code':'IyEvYmluL2Jhc2gKCmlmIFsgLWYgJy9ldGMvcmVkaGF0LXJlbGVhc2UnIF07IHRoZW4KCXl1bSBpbnN0YWxsIC15IGVwZWwtcmVsZWFzZQoJeXVtIGluc3RhbGwgLXkgZ2l0Cgl5dW0gaW5zdGFsbCAteSBlYXN5X2luc3RhbGwKCWVhc3lfaW5zdGFsbCBwaXAKCXl1bSBpbnN0YWxsIC15IHl1bS11dGlscyBkZXZpY2UtbWFwcGVyLXBlcnNpc3RlbnQtZGF0YSBsdm0yCgl5dW0tY29uZmlnLW1hbmFnZXIgLS1hZGQtcmVwbyBodHRwczovL2Rvd25sb2FkLmRvY2tlci5jb20vbGludXgvY2VudG9zL2RvY2tlci1jZS5yZXBvCgl5dW0gaW5zdGFsbCAteSBkb2NrZXItY2UKCXN5c3RlbWN0bCBzdGFydCBkb2NrZXIKCXN5c3RlbWN0bCBlbmFibGUgZG9ja2VyCglzZXJ2aWNlIGRvY2tlciBzdGFydAoJZG9ja2VyIHB1bGwgbWFuYWdlaXEvbWFuYWdlaXE6Z2FwcmluZGFzaHZpbGktNAoJZG9ja2VyIHJ1biAtLXByaXZpbGVnZWQgLWQgLXAgODQ0Mzo0NDMgbWFuYWdlaXEvbWFuYWdlaXE6Z2FwcmluZGFzaHZpbGktNAplbHNlCglhcHQtZ2V0IHVwZGF0ZSAteQoJYXB0LWdldCBpbnN0YWxsIGFwdC10cmFuc3BvcnQtaHR0cHMgY2EtY2VydGlmaWNhdGVzIGN1cmwgc29mdHdhcmUtcHJvcGVydGllcy1jb21tb24gLXkKCWN1cmwgLWZzU0wgaHR0cHM6Ly9kb3dubG9hZC5kb2NrZXIuY29tL2xpbnV4L3VidW50dS9ncGcgfCBzdWRvIGFwdC1rZXkgYWRkIC0KCWFwdC1rZXkgZmluZ2VycHJpbnQgMEVCRkNEODgKCWFkZC1hcHQtcmVwb3NpdG9yeSAiZGViIFthcmNoPWFtZDY0XSBodHRwczovL2Rvd25sb2FkLmRvY2tlci5jb20vbGludXgvdWJ1bnR1ICQobHNiX3JlbGVhc2UgLWNzKSBzdGFibGUiCglhcHQtZ2V0IHVwZGF0ZSAteQoJYXB0LWdldCBpbnN0YWxsIGRvY2tlci1jZSAteQoJc2VydmljZSBkb2NrZXIgc3RhcnQKCWRvY2tlciBwdWxsIG1hbmFnZWlxL21hbmFnZWlxOmdhcHJpbmRhc2h2aWxpLTQKCWRvY2tlciBydW4gLS1wcml2aWxlZ2VkIC1kIC1wIDg0NDM6NDQzIG1hbmFnZWlxL21hbmFnZWlxOmdhcHJpbmRhc2h2aWxpLTQKZmk='}
   ]

print "Creating control instances in DevOps Control project"

for vm in control_vms:
   print "Building %s instance."%(vm['vm'])
   try:
       send_url = 'https://console.zerostack.com/v2/clusters/%s/projects/%s/vm'%(region_id,project_id)
       data = '{"name":"%s","resources":{"server":{"type":"OS::Nova::Server","os_req":{"server":{"name":"%s","flavorRef":"4","block_device_mapping_v2":[{"device_type":"disk","disk_bus":"virtio","device_name":"/dev/vda","source_type":"volume","destination_type":"volume","delete_on_termination":true,"boot_index":"0","uuid":"{{.bootVol}}"}],"networks":[{"uuid":"%s"}],"security_groups":[{"name":"Basic"}],"metadata":{"created_by":"%s","owner":"DevOps Control","zs_internal_vm_ha":"false","delete_volume_on_termination":"true","isReservedFloatingIP":"false"},"user_data":"%s","delete_on_termination":true,"key_name":"%s"},"os:scheduler_hints":{"volume_id":"{{.bootVol}}"}}},"bootVol":{"type":"OS::Cinder::Volume","os_req":{"volume":{"availability_zone":null,"description":null,"size":20,"name":"bootVolume-ansible","volume_type":"relhighcap_type","disk_bus":"virtio","device_type":"disk","source_type":"image","device_name":"/dev/vda","bootable":true,"tenant_id":"%s","imageRef":"%s","enabled":true}}},"fip":{"type":"OS::Neutron::FloatingIP","os_req":{"floatingip":{"floating_network_id":"%s","tenant_id":"%s","port_id":"{{.port_id_0}}"}}}}}'%(vm['vm'],vm['vm'],network_id,username,vm['code'],devops_key,project_id,image_id,ext_net_id,project_id)
       r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":project_token})
       #j = json.loads(r.text)
   except Exception as e:
      print e
      sys.exit(1)
   print "Built %s with ID: %s\n\n"%(vm['vm'],r.text)

#createing the pipeline project
print "Creating the Devops BU %s Pipeline project."%(zsbuname)
pipe_project_id = None
try:
    send_url = 'https://console.zerostack.com/v2/clusters/%s/projects'%(region_id)
    data = '{"description":"Build Pipeline Project for %s devops BU.","domain_id":"%s","name":"Build Pipeline","finite_duration":false,\
          "metadata":{"templateId":"Large","custom_template":"true","userName":"%s","user_id":"%s","fingerprint":"%s","keypairName":"%s","private_key":%s,"public_key":"%s"},\
          "quota":{"compute_quota":{"cores":128,"floating_ips":64,"injected_file_content_bytes":-1,"injected_file_path_bytes":-1,"injected_files":-1,"instances":64,"key_pairs":-1,"metadata_items":-1,"ram":262144},\
          "storage_quota":{"backup_gigabytes":-1,"backups":-1,"snapshots":640,"volumes":640,"gigabytes":25600},\
          "network_quota":{"subnet":-1,"router":20,"port":-1,"network":64,"floatingip":64,"vip":-1,"pool":-1}}}'%(zsbuname,domain_id,auth_username,admin_user_id,keypair['fingerprint'],keypair['name'],json.dumps(keypair['private_key']),keypair['public_key'])
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
    j = json.loads(r.text)
    pipe_project_id = j['id']
except Exception as e:
    print e
    sys.exit(1)
print "Created build pipeline project with ID: %s\n\n"%(project_id)

print "Creating a pipeline project scoped token for %s."%(username)
pipe_token = None
try:
    send_url = auth_url+"/auth/tokens"
    data = '{"auth":{"scope":{"project":{"id":"%s"}},"identity":{"methods":["token"],"token":{"id":"%s"}}}}'%(pipe_project_id,token)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
    pipe_token = r.headers.get('X-Subject-Token')
except Exception as e:
    print e
    sys.exit(1)
print "Created pipeline project token key: %s.\n\n"%(pipe_token)

#add the basic security group
print "Creating a basic Security group for pipeline project."
pipe_secgroup_id = None
try:
    send_url = baseurl + '/neutron/v2.0/security-groups'
    data = '{"security_group":{"name":"Basic","description":"security group Basic","tenant_id":"%s"}}'%(pipe_project_id)
    r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":pipe_token})
    j = json.loads(r.text)
    pipe_secgroup_id = j['security_group']['id']
except Exception as e:
    print e
    sys.exit(1)
print "Created the basic security group with ID: %s.\n\n"%(j['security_group']['id'])

#add the ports to the security group
ports = [{'icmp':'null'},{'tcp':'22'},{'tcp':'80'},{'tcp':'443'}]
for port in ports:
    try:
        send_url = baseurl + '/neutron/v2.0/security-group-rules'
        data = '{"security_group_rule":{"direction":"ingress","port_range_min":%s,"ethertype":"IPv4","port_range_max":%s,"protocol":"%s","security_group_id":"%s","tenant_id":"%s"}}'%(port.values()[0],port.values()[0],port.keys()[0],pipe_secgroup_id,pipe_project_id)
        r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":pipe_token})
        j = json.loads(r.text.encode('latin-1'))
    except Exception as e:
        print e
        sys.exit(1)
    print "Created the basic security group rule, ID: %s.\n\n"%(j['security_group_rule']['id'])


gitjson = {"template": """heat_template_version: 2013-05-23\n\ndescription: GitLab Community Edition Single instance server\n\nparameter_groups:\n - label: GitLab CE server parameters\n   description: GitLab CE server Parameters\n   parameters:\n        - image\n        - flavor\n        - boot_volume_type\n        - boot_volume_size\n        - key_name\n        - private_network\n        - public_network\n\nparameters:\n  image:\n    type: string\n    label: Image name or ID\n    description: Image to be used for compute instance\n    constraints:\n      - custom_constraint: glance.image\n  \n  boot_volume_type:\n    type: string\n    default: relhighcap_type\n    label: Boot volume type\n    description: Boot volume type\n    constraints:\n      - custom_constraint: cinder.vtype\n        description: Volume type must be relhighcap_type or highiops_type or relhighiops_type or highcap_type\n  \n  boot_volume_size:\n    type: number\n    label: Bootable Volume Size (GB)\n    description: Bootable Volume Size in GB\n    default: 40\n\n  flavor:\n    type: string\n    label: Flavor\n    description: Type of instance (flavor) to be used\n    default: m1.large\n    constraints:\n      - custom_constraint: nova.flavor\n\n  private_network:\n    type: string\n    label: Private network name or ID\n    description: Network to attach instance to.\n    constraints:\n      - custom_constraint: neutron.network\n\n  key_name:\n    type: string\n    description: SSH key pair\n    constraints:\n      - custom_constraint: nova.keypair\n\n  public_network:\n    type: string\n    label: Public network name or ID\n    description: External network name which this instance will be attached to\n    constraints:\n      - custom_constraint: neutron.network\n\n\nresources:\n  cinder_volume:\n    type: OS::Cinder::Volume\n    properties:\n      size: { get_param: boot_volume_size }\n      volume_type: { get_param: boot_volume_type }\n      image: {get_param: image }\n\n  stack-string:\n    type: OS::Heat::RandomString\n    properties:\n      length: 6\n      sequence: lettersdigits\n\n  secgroup:\n    type: OS::Neutron::SecurityGroup\n    properties:\n      description: Open icmp ssh https ports\n      name:\n        str_replace:\n          template: gitlab-$stackstr-secgroup\n          params:\n            $stackstr:\n              get_attr:\n                - stack-string\n                - value\n      rules:\n        - protocol: tcp\n          port_range_min: 443\n          port_range_max: 443\n        - protocol: icmp\n        - protocol: tcp\n          port_range_min: 22\n          port_range_max: 22\n        - protocol: tcp\n          port_range_min: 80\n          port_range_max: 80\n\n  my_port:\n    type: OS::Neutron::Port\n    properties:\n      network: { get_param: private_network }\n      security_groups:\n        - { get_resource: secgroup }\n\n  my_instance:\n    type: OS::Nova::Server\n    depends_on: [ cinder_volume, floating_ip ]\n    properties:\n      block_device_mapping: [{ device_name: "vda", volume_id : { get_resource : cinder_volume }, delete_on_termination : "true" }]\n      flavor: { get_param: flavor }\n      key_name: { get_param: key_name }\n      networks:\n        - port: { get_resource: my_port }\n      user_data_format: RAW\n      user_data:\n        str_replace:\n                params:\n                        wc_notify: { get_attr: [gitlab_wait_handle, curl_cli] }\n                        $floating_ip: { get_attr: [floating_ip, floating_ip_address] }\n                template: |\n                        #!/bin/sh\n                        echo "found floating ip: $floating_ip"\n                        wc_notify --data-binary '{"status": "SUCCESS", "reason": "Setting up Gitlab packages."}'\n                        # MY_OS=`awk 'NR==1{print $1}' /etc/issue`\n                        # MY_OS=`awk 'NR==1{print $1}' /etc/*-release`\n                        # MY_OS=`cat /etc/*-release|grep "^ID="|cut -f 2 -d'='`\n                        MY_OS=`cat /etc/*-release|grep "^ID="|cut -f 2 -d'='|sed -e 's/^"//'  -e 's/"$//'`\n                        declare -i centos_count=0\n                        centos_count=`grep -ri "centos" /etc/*-release|wc -l`\n                        declare -i ubuntu_count=0\n                        ubuntu_count=`grep -ri "ubuntu" /etc/*-release|wc -l`\n                        if [ $ubuntu_count -gt 0 ]; then\n                                set -e -x\n                                apt-get --yes --quiet update\n                                apt-get --yes --quiet install git\n                                apt-get --yes --quiet install curl openssh-server ca-certificates\n                                curl -sS https://s3.amazonaws.com/zapps.zerostack.com/binaries/script.deb.sh | sudo bash #https://packages.gitlab.com/install/repositories/gitlab/gitlab-ce/script.deb.sh\n                                apt-get --yes --quiet install gitlab-ce\n                                sed -i "s/^external_url .*/external_url \\"http:\\/\\/$floating_ip\\"/g" /etc/gitlab/gitlab.rb\n                                gitlab-ctl reconfigure\n                                gitlab-ctl restart\n                                wc_notify --data-binary '{"status": "SUCCESS", "reason": "Gitlab setup successfully."}'\n                        elif [ $centos_count -gt 0 ]; then\n                                #disable selinux and iptables\n                                service iptables stop\n                                chkconfig iptables off\n                                sed -i 's/=enforcing/=disabled/' /etc/sysconfig/selinux\n                                setenforce 0\n                                yum -"y" install curl policycoreutils openssh-server openssh-clients\n                                yum -"y" install postfix\n                                curl -sS https://packages.gitlab.com/install/repositories/gitlab/gitlab-ce/script.rpm.sh | bash\n                                yum -"y" install gitlab-ce\n                                sed -i "s/^external_url .*/external_url \\"http:\\/\\/$floating_ip\\"/g" /etc/gitlab/gitlab.rb\n                                gitlab-ctl reconfigure\n                                gitlab-ctl restart\n                                wc_notify --data-binary '{"status": "SUCCESS", "reason": "Gitlab setup successfully."}'\n                        else\n                                wc_notify --data-binary '{"status": "FAILURE", "reason": "Operating system not supported."}'\n                        fi\n\n  floating_ip:\n    type: OS::Neutron::FloatingIP\n    properties:\n      floating_network: { get_param: public_network }\n\n  floating_ip_assoc:\n    type: OS::Neutron::FloatingIPAssociation\n    properties:\n      floatingip_id: { get_resource: floating_ip }\n      port_id: { get_resource: my_port }\n\n  gitlab_wait:\n    type: "OS::Heat::WaitCondition"\n    depends_on: my_instance\n    properties:\n      handle:\n        get_resource: gitlab_wait_handle\n      timeout: 1800\n      count: 2\n\n  gitlab_wait_handle:\n    type: "OS::Heat::WaitConditionHandle"\n\noutputs:\n  instance_ip:\n    description: Gitlab Web URL\n    value:\n        str_replace:\n                template: |\n                        http://__instance_ip\n                params:\n                        __instance_ip: { get_attr: [floating_ip, floating_ip_address] }\n  instance_name:\n    description: Gitlab Instance name\n    value: { get_attr: [my_instance, name] }\n""",
}

jenkinsjson = {"template": """heat_template_version: 2013-05-23\n# This key with value "2013-05-23" indicates that the YAML document is\n# a HOT template of the specified version.\n# This version has no relation with the application version that this template installs.\n\ndescription: Simple template to deploy a Jenkins instance.\n\nparameter_groups:\n- label: VM HA\n  description: Option To Enable VM-HA\n  parameters:\n  - zs_internal_vm_ha\n- label: Instance Parameters\n  description: Instace Specific Parameters\n  parameters:\n  - image\n  - flavor\n  - key\n  - private_network\n  - public_network\n  - boot_volume_type\n  - boot_volume_size\n  - data_volume_type\n  - data_volume_size\n- label: Proxy Parameters\n  description: Proxy environment parameters\n  parameters:\n  - proxy_type\n  - proxy_ip_port\n\nparameters:\n  image:\n    type: string\n    label: Image Name or ID\n    description: Image to be used for compute instance\n    constraints:\n      - custom_constraint: glance.image\n\n  flavor:\n    type: string\n    label: Flavor\n    description: Type of instance (flavor) to be used\n    constraints:\n      - custom_constraint: nova.flavor\n  key:\n    type: string\n    label: Key Name\n    description: Name of key-pair to be used for compute instance\n    constraints:\n      - custom_constraint: nova.keypair\n\n  private_network:\n    type: string\n    label: Private Network Name or ID\n    description: Network to attach instance to.\n    constraints:\n      - custom_constraint: neutron.network\n\n  public_network:\n    type: string\n    label: Public Network Name or ID\n    description: Network to attach instance to.\n    constraints:\n      - custom_constraint: neutron.network\n\n  boot_volume_size:\n    type: number\n    label: Bootable Volume Size (GB)\n    description: Bootable Volume Size in GB\n    default: 30\n    constraints:\n      - range: { min: 15 }\n\n  boot_volume_type:\n    type: string\n    default: relhighcap_type\n    label: Boot Volume Type\n    description: Boot volume type\n    constraints:\n      - custom_constraint: cinder.vtype\n        description: Volume type must be relhighcap_type or highiops_type or relhighiops_type or highcap_type\n\n  data_volume_type:\n    type: string\n    default: relhighcap_type\n    label: Data Volume Type\n    description: Data volume type\n    constraints:\n      - custom_constraint: cinder.vtype\n        description: Volume type must be relhighcap_type or highiops_type or relhighiops_type or highcap_type\n\n  data_volume_size:\n    type: number\n    label: Data Volume Size (GB)\n    description: Data Volume size for MySQL DB.\n    default: 20\n\n  zs_internal_vm_ha:\n    type: boolean\n    label: Enable High-Availability\n    description: VM HA enable flag\n\n  proxy_type:\n    type: string\n    label: Proxy Type\n    default: No Proxy\n    constraints:\n      - allowed_values:\n        - No Proxy\n        - HTTP Proxy\n        - HTTPS Proxy\n        - FTP Proxy\n\n  proxy_ip_port:\n    type: string\n    default: ""\n    label: Proxy Details\n    description: USERNAME:PASSWORD@IP_ADDRESS:PORT\n\nresources:\n  stack-string:\n    type: OS::Heat::RandomString\n    properties:\n      length: 4\n      character_classes:\n        - class: lowercase\n\n  boot_volume:\n    type: OS::Cinder::Volume\n    properties:\n      size: { get_param: boot_volume_size }\n      volume_type: { get_param: boot_volume_type }\n      image: {get_param: image }\n      name: { list_join: [-, [{get_param: "OS::stack_name"}, {get_resource: stack-string}, bootvolume]] }\n\n  data_volume:\n    type: OS::Cinder::Volume\n    properties:\n      size: { get_param: data_volume_size }\n      volume_type: { get_param: data_volume_type }\n      name: { list_join: [-, [{get_param: "OS::stack_name"}, {get_resource: stack-string}, datavolume]] }\n\n  secgroup:\n    type: OS::Neutron::SecurityGroup\n    properties:\n      name: { list_join: [-, [{get_param: "OS::stack_name"}, {get_resource: stack-string}, secgroup]] }\n      rules:\n        - protocol: tcp\n          port_range_min: 22\n          port_range_max: 22\n        - protocol: icmp\n        - protocol: tcp\n          port_range_min: 7070\n          port_range_max: 7070\n        - protocol: tcp\n          port_range_min: 8080\n          port_range_max: 8080\n\n\n  my_port:\n    type: OS::Neutron::Port\n    properties:\n      network: { get_param: private_network }\n      name: { list_join: [-, [{get_param: "OS::stack_name"}, {get_resource: stack-string}, port]] }\n      security_groups:\n        - { get_resource: secgroup }\n\n  jenkins_instance:\n    type: OS::Nova::Server\n    properties:\n      block_device_mapping: [{ device_name: "vda", volume_id : { get_resource : boot_volume }, delete_on_termination : "true" },{ device_name: "vdb", volume_id : { get_resource : data_volume }, delete_on_termination : "false" }]\n      image: { get_param: image }\n      name: { list_join: [-, [{get_param: "OS::stack_name"}, {get_resource: stack-string}, instance]] }\n      flavor: { get_param: flavor }\n      key_name: { get_param: key }\n      networks:\n        - port: { get_resource: my_port }\n      metadata:\n        zs_internal_vm_ha:\n          "Fn::Select":\n          - str_replace:\n              template: "is_ha_enabled"\n              params:\n                is_ha_enabled: {get_param: zs_internal_vm_ha}\n          - { "True": "true", "False": "false"}\n        zs_internal_desired_state: "ACTIVE"\n      user_data_format: RAW\n      user_data:\n        str_replace:\n          template: |\n            #!/bin/bash -x\n            exec &> >(gawk '{ print strftime("[%Y-%m-%d %H:%M:%S]"), $0 }' | tee -a /var/tmp/install.log)\n\n            DIR=data\n            DEVNAME=/dev/vdb\n            FSTYPE=ext3\n\n            # create FS for Data Volume\n            (echo m; echo n; echo p; echo 1; echo ; echo ; echo w) | fdisk $DEVNAME\n            mkfs -t $FSTYPE $DEVNAME\n\n            # Mount FS and add an entry to fstab\n            mkdir /$DIR\n            mount $DEVNAME /$DIR\n            sh -c "echo $DEVNAME /$DIR ext3 defaults,noatime,nofail 0 0 >> /etc/fstab"\n            #mkdir -p /data/\n\n            ############ Installing Jenkins Server on single node #####################\n            wc_notify --data-binary '{"status": "SUCCESS", "reason": "Setting up Jenkins"}'\n            OSDISTRO=$(awk 'NR==1{print $1}' /etc/issue)\n            ### Set hostname #######\n            sysctl kernel.hostname="jenkins.local.in"\n            IP=$(/sbin/ifconfig eth0 | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}')\n            sh -c "echo $IP jenkins.local.in >> /etc/hosts"\n\n            declare -i centos_count=0\n            centos_count=`grep -ri "centos" /etc/*-release|wc -l`\n            declare -i ubuntu_count=0\n            ubuntu_count=`grep -ri "ubuntu" /etc/*-release|wc -l`\n            #OSDISTRO=$(lsb_release -i | awk {'print $3'})\n            if [ $ubuntu_count -gt 0 ]; then\n               ### Set hostname #######\n               sh -c 'echo "jenkins.local.in" > /etc/hostname'\n            case "__proxy_type__" in\n             "HTTP Proxy")\n                  export http_proxy=http://__proxy_ip_port__\n                  echo 'Acquire::http::Proxy "http://__proxy_ip_port__";' >> /etc/apt/apt.conf\n                  echo 'http_proxy = http://__proxy_ip_port__' >> /etc/wgetrc\n                  echo 'https_proxy = https://__proxy_ip_port__' >> /etc/wgetrc\n                  echo 'use_proxy = on' >> /etc/wgetrc\n                  ;;\n             "HTTPS Proxy")\n                  export https_proxy=https://__proxy_ip_port__\n                  echo 'Acquire::https::Proxy "https://__proxy_ip_port__";' >> /etc/apt/apt.conf\n                  echo 'https_proxy = https://__proxy_ip_port__' >> /etc/wgetrc\n                  echo 'http_proxy = http://__proxy_ip_port__' >> /etc/wgetrc\n                  echo 'use_proxy = on' >> /etc/wgetrc\n                  ;;\n             "FTP Proxy")\n                  export ftp_proxy=ftp://__proxy_ip_port__\n                  echo 'Acquire::ftp::Proxy "ftp://__proxy_ip_port__";' >> /etc/apt/apt.conf\n                  echo 'ftp_proxy = ftp://__proxy_ip_port__' >> /etc/wgetrc\n                  echo 'http_proxy = http://__proxy_ip_port__' >> /etc/wgetrc\n                  echo 'https_proxy = https://__proxy_ip_port__' >> /etc/wgetrc\n                  echo 'use_proxy = on' >> /etc/wgetrc\n                  ;;\n            esac\n               ### Installing java #########\n               wget https://images.zerostack.com/zapps/binaries/InstallCert.java -O /data/InstallCert.java\n               echo oracle-java8-installer shared/accepted-oracle-license-v1-1 select true | /usr/bin/debconf-set-selections\n               wget https://images.zerostack.com/zapps/java/jdk-8u161-linux-x64.tar.gz\n               mkdir -p /usr/lib/jvm\n               tar -zxf  jdk-8u161-linux-x64.tar.gz -C /usr/lib/jvm\n               apt-get update\n               wget https://images.zerostack.com/zapps/java/java-common_0.51_all.deb\n               dpkg --force-all -i java-common_0.51_all.deb\n               update-alternatives --install /usr/bin/java java /usr/lib/jvm/java-8-oracle/bin/java 100\n               update-alternatives --install /usr/bin/javac javac /usr/lib/jvm/java-8-oracle/bin/javac 100\n               sudo update-alternatives --config java\n               rm -rf java-common_0.51_all.deb jdk-8u161-linux-x64.tar.gz\n               ln -s /usr/lib/jvm/java-8-oracle/bin/keytool /usr/bin/ -f\n               cd /data/\n               /usr/lib/jvm/java-8-oracle/bin/javac /data/InstallCert.java\n               echo "" | java InstallCert console.zerostack.com:443\n               keytool -exportcert -alias console.zerostack.com-1 -keystore jssecacerts -storepass changeit -file console.zerostack.com.cer\n               echo "yes" | keytool -importcert -alias console.zerostack.com -keystore /usr/lib/jvm/java-8-oracle/jre/lib/security/cacerts -storepass changeit -file console.zerostack.com.cer\n\n               ### Adding Jenkins repos and installing Jenkins using apt-get\n               wget -q -O - http://pkg.jenkins-ci.org/debian/jenkins-ci.org.key | apt-key add -\n               sh -c 'echo deb http://pkg.jenkins-ci.org/debian binary/ > /etc/apt/sources.list.d/jenkins.list'\n               apt-get update\n               apt-get install jenkins=2.114 curl -y\n               update-rc.d jenkins enable\n               mkdir -p /data/jenkins\n               chown -R jenkins:jenkins /data/jenkins\n               perl -pi.bak -e "s%/var/lib%/data%" /etc/default/jenkins\n               service jenkins restart\n               sleep 10s\n               sed -i "s/-1/7070/g" /data/jenkins/config.xml\n\n               #### Updating plugins ########\n               curl -L https://updates.jenkins-ci.org/update-center.json | sed '1d;$d' > /data/jenkins/updates/default.json\n               chown jenkins:jenkins /data/jenkins/updates/default.json\n               service jenkins restart\n               sleep 10s\n               ### Download jenkins-cli.jar file and installing the plugins ###\n               cd /data/jenkins\n               curl -O http://jenkins.local.in:8080/jnlpJars/jenkins-cli.jar\n               if [ -f /data/jenkins/jenkins-cli.jar ]; then\n                  java -jar /data/jenkins/jenkins-cli.jar -s http://jenkins.local.in:8080 login --username=admin --password=$(cat /data/jenkins/secrets/initialAdminPassword)\n                  #echo 'jenkins.model.Jenkins.instance.securityRealm.createAccount("user1", "password123")' | java -jar /data/jenkins/jenkins-cli.jar -s http://jenkins.local.in:8080/ groovy =\n                  echo 'hpsr=new hudson.security.HudsonPrivateSecurityRealm(false); hpsr.createAccount("jenkins", "password123")' | java -jar /data/jenkins/jenkins-cli.jar -s http://jenkins.local.in:8080 groovy =\n                  plugins=__plugins__\n                  for item in $(echo $plugins | sed "s/,/ /g");\n                  do\n                      java -jar /data/jenkins/jenkins-cli.jar -s http://jenkins.local.in:8080 install-plugin $item\n                  done\n               fi\n            case "__proxy_type__" in\n             "HTTP Proxy")\n                  mkdir -p /data/jenkins/init.groovy.d\n                  cd /data/jenkins/init.groovy.d\n                  wget https://images.zerostack.com/zapps/binaries/basic-security.groovy\n                  cd /data/jenkins\n                  wget https://images.zerostack.com/zapps/binaries/jenkins-version-211-plugins.tar\n                  tar -xf jenkins-version-211-plugins.tar\n                  echo 'HiqRprXwlp' > /data/jenkins/secrets/initialAdminPassword\n                  ;;\n             "HTTPS Proxy")\n                  mkdir -p /data/jenkins/init.groovy.d\n                  cd /data/jenkins/init.groovy.d\n                  wget https://images.zerostack.com/zapps/binaries/basic-security.groovy\n                  cd /data/jenkins\n                  wget https://images.zerostack.com/zapps/binaries/jenkins-version-211-plugins.tar\n                  tar -xf jenkins-version-211-plugins.tar\n                  echo 'HiqRprXwlp' > /data/jenkins/secrets/initialAdminPassword\n                  ;;\n             "FTP Proxy")\n                  mkdir -p /data/jenkins/init.groovy.d\n                  cd /data/jenkins/init.groovy.d\n                  wget https://images.zerostack.com/zapps/binaries/basic-security.groovy\n                  cd /data/jenkins\n                  wget https://images.zerostack.com/zapps/binaries/jenkins-version-211-plugins.tar\n                  tar -xf jenkins-version-211-plugins.tar\n                  echo 'HiqRprXwlp' > /data/jenkins/secrets/initialAdminPassword\n                  ;;\n            esac\n               service jenkins restart\n               service jenkins status\n               status=$(echo $?)\n            elif [ $centos_count -gt 0 ]; then\n               ######### Centos6 disabled selinux and stop iptables #########\n            case "__proxy_type__" in\n             "HTTP Proxy")\n                  export http_proxy=http://__proxy_ip_port__\n                  echo 'proxy=http://__proxy_ip_port__' >> /etc/yum.conf\n                  echo 'http_proxy = http://__proxy_ip_port__' >> /etc/wgetrc\n                  echo 'https_proxy = https://__proxy_ip_port__' >> /etc/wgetrc\n                  echo 'use_proxy = on' >> /etc/wgetrc\n                  ;;\n             "HTTPS Proxy")\n                  export https_proxy=https://__proxy_ip_port__\n                  echo 'proxy=https://__proxy_ip_port__' >> /etc/yum.conf\n                  echo 'https_proxy = https://__proxy_ip_port__' >> /etc/wgetrc\n                  echo 'http_proxy = http://__proxy_ip_port__' >> /etc/wgetrc\n                  echo 'use_proxy = on' >> /etc/wgetrc\n                  ;;\n             "FTP Proxy")\n                  export ftp_proxy=ftp://__proxy_ip_port__\n                  echo 'proxy=ftp://__proxy_ip_port__' >> /etc/yum.conf\n                  echo 'ftp_proxy = ftp://__proxy_ip_port__' >> /etc/wgetrc\n                  echo 'http_proxy = http://__proxy_ip_port__' >> /etc/wgetrc\n                  echo 'https_proxy = https://__proxy_ip_port__' >> /etc/wgetrc\n                  echo 'use_proxy = on' >> /etc/wgetrc\n                  ;;\n            esac\n               /etc/init.d/iptables stop\n               chkconfig iptables off\n               chkconfig ip6tables off\n               setenforce 0\n               sed -i "s/=enforcing/=disabled/g" /etc/sysconfig/selinux\n\n               ############ Install Standard tool ##########\n               yum install wget curl vim -y\n               yum remove java\n               #yum install java-1.7.0-openjdk -y\n               yum install java-1.8.0-openjdk-devel -y\n               ### Installing java #########\n               cd /data/\n               wget https://images.zerostack.com/zapps/binaries/InstallCert.java -O /data/InstallCert.java\n               /usr/lib/jvm/java/bin/javac /data/InstallCert.java\n               echo "" | java InstallCert console.zerostack.com:443\n               keytool -exportcert -alias console.zerostack.com-1 -keystore jssecacerts -storepass changeit -file console.zerostack.com.cer\n               echo "yes" | keytool -importcert -alias console.zerostack.com -keystore /usr/lib/jvm/java-1.8.0-openjdk-1.8.0.91-1.b14.el6.x86_64/jre/lib/security/cacerts -storepass changeit -file console.zerostack.com.cer\n               #### Add the Jenkins repository to the yum repos, and install Jenkins.\n               wget -O /etc/yum.repos.d/jenkins.repo http://pkg.jenkins-ci.org/redhat/jenkins.repo\n               rpm --import https://jenkins-ci.org/redhat/jenkins-ci.org.key\n               sed -i 's/gpgcheck=1/gpgcheck=0/g' /etc/yum.repos.d/jenkins.repo\n               yum install jenkins-2.114 -y\n               chkconfig jenkins on\n               mkdir -p /data/jenkins\n               chown -R jenkins:jenkins /data/jenkins\n               perl -pi.bak -e "s%/var/lib%/data%" /etc/sysconfig/jenkins\n               service jenkins restart\n               sleep 10s\n               sed -i "s/-1/7070/g" /data/jenkins/config.xml\n\n               #### Updating plugins ########\n               wget -O /data/jenkins/updates/default.json https://updates.jenkins-ci.org/update-center.json\n               chown jenkins:jenkins /data/jenkins/updates/default.json\n               service jenkins restart\n               sleep 10s\n               ### Download jenkins-cli.jar file and installing the plugins ###\n               cd /data/jenkins\n               curl -O http://jenkins.local.in:8080/jnlpJars/jenkins-cli.jar\n               if [ -f /data/jenkins/jenkins-cli.jar ]; then\n                  java -jar /data/jenkins/jenkins-cli.jar -s http://jenkins.local.in:8080 login --username=admin --password=$(cat /data/jenkins/secrets/initialAdminPassword)\n                  echo 'hpsr=new hudson.security.HudsonPrivateSecurityRealm(false); hpsr.createAccount("jenkins", "password123")' | java -jar /data/jenkins/jenkins-cli.jar -s http://jenkins.local.in:8080 groovy =\n                  plugins=__plugins__\n                  for item in $(echo $plugins | sed "s/,/ /g");\n                  do\n                      java -jar /data/jenkins/jenkins-cli.jar -s http://jenkins.local.in:8080 install-plugin $item\n                  done\n               fi\n            case "__proxy_type__" in\n             "HTTP Proxy")\n                  mkdir -p /data/jenkins/init.groovy.d\n                  cd /data/jenkins/init.groovy.d\n                  wget https://images.zerostack.com/zapps/binaries/basic-security.groovy\n                  cd /data/jenkins\n                  wget https://images.zerostack.com/zapps/binaries/jenkins-version-211-plugins.tar\n                  tar -xf jenkins-version-211-plugins.tar\n                  echo 'HiqRprXwlp' > /data/jenkins/secrets/initialAdminPassword\n                  ;;\n             "HTTPS Proxy")\n                  mkdir -p /data/jenkins/init.groovy.d\n                  cd /data/jenkins/init.groovy.d\n                  wget https://images.zerostack.com/zapps/binaries/basic-security.groovy\n                  cd /data/jenkins\n                  wget https://images.zerostack.com/zapps/binaries/jenkins-version-211-plugins.tar\n                  tar -xf jenkins-version-211-plugins.tar\n                  echo 'HiqRprXwlp' > /data/jenkins/secrets/initialAdminPassword\n                  ;;\n             "FTP Proxy")\n                  mkdir -p /data/jenkins/init.groovy.d\n                  cd /data/jenkins/init.groovy.d\n                  wget https://images.zerostack.com/zapps/binaries/basic-security.groovy\n                  cd /data/jenkins\n                  wget https://images.zerostack.com/zapps/binaries/jenkins-version-211-plugins.tar\n                  tar -xf jenkins-version-211-plugins.tar\n                  echo 'HiqRprXwlp' > /data/jenkins/secrets/initialAdminPassword\n                  ;;\n            esac\n               service jenkins restart\n               service jenkins status\n               status=$(echo $?)\n            fi\n            ################### Checking redis server service is running or not #########################\n            if [ $status -eq 0 ]; then\n                wc_notify --data-binary '{"status": "SUCCESS", "reason": "Jenkins Server Installation Completed"}'\n            else\n                wc_notify --data-binary '{"status": "FAILURE", "reason": "Error While Installing Jenkins Server"}'\n            fi\n          params:\n            __proxy_ip_port__: { get_param: proxy_ip_port }\n            __proxy_type__: { get_param: proxy_type }\n            __plugins__: ssh,git,openstack-cloud,subversion\n            wc_notify: { get_attr: [jenkins_wait_handle, curl_cli] }\n\n  floating_ip:\n      type: OS::Neutron::FloatingIP\n      properties:\n        floating_network: { get_param: public_network }\n\n  floating_ip_assoc:\n    type: OS::Neutron::FloatingIPAssociation\n    properties:\n      floatingip_id: { get_resource: floating_ip }\n      port_id: { get_resource: my_port }\n\n  jenkins_wait:\n    type: "OS::Heat::WaitCondition"\n    depends_on: jenkins_instance\n    properties:\n      handle:\n        get_resource: jenkins_wait_handle\n      timeout: 1800\n      count: 2\n\n  jenkins_wait_handle:\n    type: "OS::Heat::WaitConditionHandle"\n\noutputs:\n  instance_public_ip:\n    description: Jenkins Server Public IP\n    value:\n      str_replace:\n        template: |\n          __instance_ip__:8080\n        params:\n          __instance_ip__: { get_attr: [floating_ip, floating_ip_address] }\n\n  username:\n    description: Jenkins Username\n    value: admin\n\n  password:\n    description: Jenkins Password\n    value: password will be at /data/jenkins/secrets/initialAdminPassword\n"""
}

gitjson = json.dumps(gitjson['template'])
jenkinsjson = json.dumps(jenkinsjson['template'])

#get the app stack templates
print "Gathering the templates"
try:
    send_url = 'https://console.zerostack.com/v2/clusters/%s/app_templates'%(region_id)
    r = requests.get(send_url,verify = False,headers={"content-type":"application/json","X-Auth-Token":pipe_token})
    templates = json.loads(r.text)
except Exception as e:
    print e
    sys.exit(1)

for template in templates:
    if template['name'] == 'GitLab':
        #print template['template_content']
        print "Creating GitLab code repository."
        try:
            send_url = baseurl + '/heat/v1/%s/stacks'%(pipe_project_id)

            data = '{"tenant_id":"%s",\
                   "stack_name":"gitlab",\
                   "parameters":{"image":"%s",\
                                 "flavor":"m1.large",\
                                 "boot_volume_type":"highcap_type",\
                                 "boot_volume_size":40,\
                                 "key_name":"%s",\
                                 "private_network":"%s",\
                                 "public_network":"%s"},\
                                 "template":%s}'%(pipe_project_id,image_id,devops_key,network_id,ext_net_id,gitjson)
            r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":pipe_token,"ZS-Template-Id":template['id']})
            j = json.loads(r.text)
        except Exception as e:
            print e
            sys.exit(1)

        print "Building the Gitlab code repository, ID: %s\n"%(j['stack']['id'])

    if template['name'] == 'Jenkins':
        print "Creating Jenkins CI/CD piplein tool."
        try:
            send_url = baseurl + '/heat/v1/%s/stacks'%(pipe_project_id)
            data = '{"tenant_id":"%s",\
                   "stack_name":"Jenkins",\
                   "parameters":{"zs_internal_vm_ha":false,\
                                 "image":"%s",\
                                 "flavor":"m1.large",\
                                 "key":"%s",\
                                 "private_network":"%s",\
                                 "public_network":"%s",\
                                 "boot_volume_type":"highcap_type",\
                                 "boot_volume_size":30,\
                                 "data_volume_type":"highcap_type",\
                                 "data_volume_size":20,\
                                 "proxy_type":"No Proxy"},\
                                 "template":%s}'%(pipe_project_id,image_id,devops_key,network_id,ext_net_id,jenkinsjson)
            r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":pipe_token,"ZS-Template-Id":template['id']})
            j = json.loads(r.text)
        except Exception as e:
            print e
            sys.exit(1)
        print "Building the Jenkins CI/CD toolset, ID: %s\n"%(j['stack']['id'])

pipeline_vms = ['Container Repo']
print "Creating build pipeline support instances in Pipeline project"

for vm in pipeline_vms:
   print "Building %s instance."%(vm)
   try:
       send_url = 'https://console.zerostack.com/v2/clusters/%s/projects/%s/vm'%(region_id,pipe_project_id)
       data = '{"name":"%s","resources":{"server":{"type":"OS::Nova::Server","os_req":{"server":{"name":"%s","flavorRef":"4","block_device_mapping_v2":[{"device_type":"disk","disk_bus":"virtio","device_name":"/dev/vda","source_type":"volume","destination_type":"volume","delete_on_termination":true,"boot_index":"0","uuid":"{{.bootVol}}"}],"networks":[{"uuid":"%s"}],"security_groups":[{"name":"Basic"}],"metadata":{"created_by":"%s","owner":"DevOps Control","zs_internal_vm_ha":"false","delete_volume_on_termination":"true","isReservedFloatingIP":"false"},"user_data":"","delete_on_termination":true,"key_name":"%s"},"os:scheduler_hints":{"volume_id":"{{.bootVol}}"}}},"bootVol":{"type":"OS::Cinder::Volume","os_req":{"volume":{"availability_zone":null,"description":null,"size":20,"name":"bootVolume-ansible","volume_type":"relhighcap_type","disk_bus":"virtio","device_type":"disk","source_type":"image","device_name":"/dev/vda","bootable":true,"tenant_id":"%s","imageRef":"%s","enabled":true}}},"fip":{"type":"OS::Neutron::FloatingIP","os_req":{"floatingip":{"floating_network_id":"%s","tenant_id":"%s","port_id":"{{.port_id_0}}"}}}}}'%(vm,vm,network_id,username,devops_key,pipe_project_id,image_id,ext_net_id,pipe_project_id)
       r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":pipe_token})
       #j = json.loads(r.text)
   except Exception as e:
      print e
      sys.exit(1)
   print "Built %s with ID: %s\n\n"%(vm,r.text)

#build all of the other devops projects
projects = ['Blue','Green','Canary','Development','TestQA']
for project in projects:
    print "Creating the Devops BU %s %s project."%(zsbuname,project)
    project_id = None
    try:
        send_url = 'https://console.zerostack.com/v2/clusters/%s/projects'%(region_id)
        data = '{"description":"Build %s Project for %s devops BU.","domain_id":"%s","name":"%s","finite_duration":false,\
          "metadata":{"templateId":"Large","custom_template":"true","userName":"%s","user_id":"%s","fingerprint":"%s","keypairName":"%s","private_key":%s,"public_key":"%s"},\
          "quota":{"compute_quota":{"cores":128,"floating_ips":64,"injected_file_content_bytes":-1,"injected_file_path_bytes":-1,"injected_files":-1,"instances":64,"key_pairs":-1,"metadata_items":-1,"ram":262144},\
          "storage_quota":{"backup_gigabytes":-1,"backups":-1,"snapshots":640,"volumes":640,"gigabytes":25600},\
          "network_quota":{"subnet":-1,"router":20,"port":-1,"network":64,"floatingip":64,"vip":-1,"pool":-1}}}'%(project,zsbuname,domain_id,project,auth_username,admin_user_id,keypair['fingerprint'],keypair['name'],json.dumps(keypair['private_key']),keypair['public_key'])
        r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
        j = json.loads(r.text)
        project_id = j['id']
    except Exception as e:
        print e
        sys.exit(1)
    print "Created control project with ID: %s\n\n"%(project_id)

    #add the admin
    print "Adding the admin account to the devops control project."
    try:
        send_url = auth_url + '/projects/%s/users/%s/roles/%s'%(project_id,user_id,admin_id)
        r = requests.put(send_url,verify = False,headers={"content-type":"application/json","X-Auth-Token":token})
    except Exception as e:
        print e
        sys.exit(1)
    print "Admin user added.\n\n"

    #add the basic security group
    print "Creating a basic Security group for %s BU."%(zsbuname)
    secgroup_id = None
    try:
        send_url = baseurl + '/neutron/v2.0/security-groups'
        data = '{"security_group":{"name":"Basic","description":"security group Basic","tenant_id":"%s"}}'%(project_id)
        r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
        j = json.loads(r.text)
        secgroup_id = j['security_group']['id']
    except Exception as e:
        print e
        sys.exit(1)
    print "Created the basic security group with ID: %s.\n\n"%(j['security_group']['id'])

    #add the ports to the security group
    ports = [{'icmp':'null'},{'tcp':'22'},{'tcp':'80'},{'tcp':'443'}]
    for port in ports:
        try:
            send_url = baseurl + '/neutron/v2.0/security-group-rules'
            data = '{"security_group_rule":{"direction":"ingress","port_range_min":%s,"ethertype":"IPv4","port_range_max":%s,"protocol":"%s","security_group_id":"%s","tenant_id":"%s"}}'%(port.values()[0],port.values()[0],port.keys()[0],secgroup_id,project_id)
            r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
            j = json.loads(r.text.encode('latin-1'))
        except Exception as e:
            print e
            sys.exit(1)
        print "Created the basic security group rule, ID: %s.\n\n"%(j['security_group_rule']['id'])

    print "Creating a %s scoped token for %s."%(project,username)
    project_token = None
    try:
        send_url = auth_url+"/auth/tokens"
        data = '{"auth":{"scope":{"project":{"id":"%s"}},"identity":{"methods":["token"],"token":{"id":"%s"}}}}'%(project_id,token)
        r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":token})
        project_token = r.headers.get('X-Subject-Token')
    except Exception as e:
        print e
        sys.exit(1)
    print "Created project token key: %s.\n\n"%(project_token)

    print "Building %s instance."%(project)
    try:
        send_url = 'https://console.zerostack.com/v2/clusters/%s/projects/%s/vm'%(region_id,project_id)
        data = '{"name":"%s","resources":{"server":{"type":"OS::Nova::Server","os_req":{"server":{"name":"%s","flavorRef":"4","block_device_mapping_v2":[{"device_type":"disk","disk_bus":"virtio","device_name":"/dev/vda","source_type":"volume","destination_type":"volume","delete_on_termination":true,"boot_index":"0","uuid":"{{.bootVol}}"}],"networks":[{"uuid":"%s"}],"security_groups":[{"name":"Basic"}],"metadata":{"created_by":"%s","owner":"DevOps Control","zs_internal_vm_ha":"false","delete_volume_on_termination":"true","isReservedFloatingIP":"false"},"user_data":"","delete_on_termination":true,"key_name":"%s"},"os:scheduler_hints":{"volume_id":"{{.bootVol}}"}}},"bootVol":{"type":"OS::Cinder::Volume","os_req":{"volume":{"availability_zone":null,"description":null,"size":20,"name":"bootVolume-ansible","volume_type":"relhighcap_type","disk_bus":"virtio","device_type":"disk","source_type":"image","device_name":"/dev/vda","bootable":true,"tenant_id":"%s","imageRef":"%s","enabled":true}}},"fip":{"type":"OS::Neutron::FloatingIP","os_req":{"floatingip":{"floating_network_id":"%s","tenant_id":"%s","port_id":"{{.port_id_0}}"}}}}}'%(project,project,network_id,username,devops_key,project_id,image_id,ext_net_id,project_id)
        r = requests.post(send_url,verify = False,data = data,headers={"content-type":"application/json","X-Auth-Token":project_token})
        #j = json.loads(r.text)
    except Exception as e:
       print e
       sys.exit(1)
    print "Built %s instance with ID: %s\n\n"%(project,r.text)