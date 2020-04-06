# hyper-128t

configuration scripts for various hypervisors to run 128T virtual machines

## Requirements

The hyper-128t scripts require Python 3 to be executed. The scripts have been tested on macOS and CentOS 7:

```
$ yum install -y git python3 python-virtualenv
```

## Installation

After checking out the git repository, create a python virtual environment, and install needed libraries using pip:

```
$ git clone https://github.com/128technology/hyper-128t.git
$ cd multi-128t/
$ virtualenv -p python3 --system-site-packages venv
$ venv/bin/pip install -r requirements.txt
```

Now, the system is ready to run the scripts:

```
$ venv/bin/python create_deployment.py --help
usage: Create 128T deployment in virtualized infrastructure.
       [-h] [--assumeyes] [--debug] [--config-file CONFIG_FILE]
       --parameters-file PARAMETERS_FILE

optional arguments:
  -h, --help            show this help message and exit
  --assumeyes, -y       answer yes for all questions
  --debug, -d           show debug messages
  --config-file CONFIG_FILE, -c CONFIG_FILE
                        config filename
  --parameters-file PARAMETERS_FILE, -p PARAMETERS_FILE
                        parameter filename
```

## Configuration

Most scripts require two command line arguments:

* `--config-file` (or `-c`) - contains global settings, e.g. host names and credentials for the hypervisors used. When omitted `config.yaml` is assumed.
* `--parameters-file` (or `-p`) - contains deployment specific parameters, e.g. deployment name, ip adresses, passwords, template files.

The settings in config file depend on the selected hypervisor provider. The following file gives an example for a promox setup:

```
$ cat config.yaml
provider: proxmox
hypervisors:
  - promox-node-1.example.com
  - promox-node-2.example.com
username: root@pam
password: XXXXXXXXXXXXXXXXXXXX
reference_template: 20200401-128t-template
```

A new deployment called `acme` consisting of a conductor and a headend router can be created using a parameters file like this:

```
$ cat parameters-acme.yaml
deployment_name: acme
domain_name: sdwan.msp.invalid
license_file: acme-license.pem
conductor:
  interfaces:
    wan:
      address: 10.128.1.128/16
      gateway: 10.128.1.1
    ha_sync:
      address: 172.28.1.128/16
  passwords:
    admin: secret
    root: high.secret
    t128: very.secret
  ssh_keys:
    root: file:id_rsa_acme.pub
    t128: file:id_rsa_acme.pub
    netconf: file:id_rsa_acme.pub
  # config_templates are searched in directory "config_templates"
  config_template: conductor.j2
  gps: +51.061943+010.364245/
  location: ACME datacenter
headend:
  interfaces:
    wan:
      address: 10.128.1.129/16
      gateway: 10.128.1.1
    mpls:
      address: 192.168.1.129/16
      gateway: 192.168.1.1
  passwords:
    admin: secret
    root: high.secret
    t128: very.secret
  ssh_keys:
    root: file:id_rsa_acme.pub
    t128: file:id_rsa_acme.pub
  config_template: router.j2
```

## Create a new deployment

After a parameters file has been prepared, call `create_deployment.py`:

```
$ venv/bin/python create_deployment.py -p parameters-acme.yaml
INFO: Creating a new VM:
 * ID: 100
 * Name: acme-conductor
 * Host: promox-node-1.example.com
Continue [yN]? y
INFO: VM is being created. This may take some time...
INFO: Configuration committed successfully
INFO: Conductor IP address(es): 10.128.1.128
INFO: Creating a new VM:
 * ID: 101
 * Name: acme-headend
 * Host: promox-node-1.example.com
Continue [yN]? y
INFO: VM is being created. This may take some time...
INFO: Configuration committed successfully
```
