# Solution Deployer

## Prerequisites

It works on Python 3.11 (on earlier Python versions - cannot guarantee). 

The following additional modules should be enough:

```
pip3 install paramiko paramiko-expect jinja2 
```

Finally, it uses [Newman](https://learning.postman.com/docs/collections/using-newman-cli/installing-running-newman/) to run Postman collections. Typically, you can install it like this:

```
npm install -g newman
```

And of course, in order to run the above, first you must install [NodeJs / NPM](https://nodejs.org/en/learn/getting-started/how-to-install-nodejs). 

## File Structure

- The `tenants` directory contains sub-directories for each Tenant (or Project). This is where the Deployer will look for the 
  configuration files. Mainly for the `config.yaml` (you will find it under each tenant directory). It is a good practice to 
  put any tenant-specific files there, including any Jinja, CSV etc. referred in the tasks for that tenant. 

- The main "frontend" of the Deployer is `autodeploy.py`. That's the main tool you must run in order to deploy your tenant/project. 

- The "backend" is in the `orch_base.py`, as well as under the `fmg_api` directory. You will never run those scripts directly. 

- There are some other "frontend" Python scripts written for tailored purposes (e.g. to generate the CSV inventory etc.), 
  but those are generally used by someone who knows for what exactly they were written. Most probably, they are performing some 
  configuration tasks related to the SD-WAN HoL published on FNDN. They will use the same Deployer "backend". 

- Finally, there are Bash scripts which serve as wrappers: they prepare the ground for the Deployer to run. For example, they 
  download the necessary files from GitHub and so on. Again, they are custom-made, mostly for the SD-WAN HoL published on FNDN. 

## Usage

Before running the Deployer, you must specify the tenant (project). You can do it in two ways:

1. Set an environment variable `ORCH_TENANT`. For example:

   ```
   export ORCH_TENANT=CustomerU
   ```

2. Create a file `.orch_tenant` in the Deployer directory, containing the default name of the tenant, 
   to use when the ORCH_TENANT env.var is NOT set. For example:

   ```
   # cat .orch_tenant 
   CustomerU
   ```

In both cases, the result is that the Deployer will look for the tenant configuration under `tenants/CustomerU/config.yaml`.

After specifying the tenant, you can simply run the Deployer, and the rest will be determined by the respective `config.yaml`:

```
./autodeploy.py
```

By default, the Deployer will execute all the tenant tasks from the `config.yaml`. 
You can use the flags `--tags` and `--skip-tags` to specify the list of tags to be executed / skipped. 

## Config.yaml

Here is an example demonstrating the general syntax of the `config.yaml` with added comments:

```yaml
---
# FMG details to be used by the Deployer for API calls
fmg_host: 192.168.0.15
fmg_user: admin
fmg_password: fortinet
fmg_adom: CustomerU

# Postman collection to be used for the tasks with type = postman
postman_collection: tenants/shared/Managed_SDWAN_7_4_x.postman.json
# List of tags to skip when running the Deployer without explicit --tags / --skip-tags flags
default_skip_tags: lab

# FGT details, including the FMG IP from FGT perspective
fgfm_ip: 192.168.0.15
fgt_user: admin
fgt_password: fortinet

# List of FGTs
sites:
  site1-1:
    ip: 192.168.0.31
  site1-2:
    ip: 192.168.0.32
  #...

# List of tasks
tasks:
  - name: Create Foundation
    type: postman
    folder: Foundation
    tag: foundation
  - name: Import Project Template (dyn_bgp only)
    type: cli_templates
    src: tenants/CustomerU/Project.dyn_bgp.j2
    rename: Project
    tag: lab
  # ...
```

See some of the provided tenant configs for more examples. 

## Tasks

Each task has the following parameters:

- `name` - the name of the tasks (for display purposes mainly)
- `type` - one of the supported types (see below)
- `tag` - a tag or a list of comma-delimited tags to include/exclude tasks from the run (optional)
- Additional arguments (zero or more), as defined by the task type

Let's list all the supported task types and describe the arguments for each one of them.

### `type: postman`

Run one or more API calls from the Postman collection defined under the global `postman_collection` parameter.

Supported arguments:

| Argument | Values   | Description                                   | Required | Default |
|----------|----------|-----------------------------------------------|----------|---------|
| `folder` | string   | API call or folder name to run (using Newman) | yes      | -       |
| `vars`   | filename | YAML file with variables (to pass to Newman)  | no       | -       |

In addition to the arbitrary variables optionally specified by the `vars` argument, the following variables are always passed to Newman
(this is currently hard-coded):

| Variable   | Description                                              |
|------------|----------------------------------------------------------|
| `ip`       | FMG IP from the `fmg_host` parameter                     |
| `adom`     | FMG ADOM from the `fmg_adom` parameter                   |
| `session`  | Session token (FMG login call will be run automatically) |

Therefore, it is important that your Postman collection uses these variables in the calls.
For example, the JSON API endpoint must be: 

```
https://{{ip}}/jsonrpc
```

### `type: cli_templates`

Import CLI Template files into the FMG. 

Supported arguments:

| Argument | Values           | Description                                | Required | Default                               |
|----------|------------------|--------------------------------------------|----------|---------------------------------------|
| `src`    | filename(s)      | Template files (shell wildcards supported) | yes      | -                                     |
| `rename` | string           | Target name of the Template on FMG         | no       | Original filename (without extension) |
| `syntax` | 'jinja' or 'cli' | CLI Template type                          | no       | 'jinja'                               |
| `prerun` | boolean          | Pre-run CLI Template                       | no       | false                                 |


### `type: model_devices`

Create Model Devices on the FMG, using an inventory CSV file. The CSV file format is the same as supported by the FMG for the 
bulk Model Device creation. 

The task will:

- Create the Model Devices
- Set per-device Variables
- Assign the Pre-run CLI Template

Supported arguments:

| Argument | Values      | Description                    | Required | Default                      |
|----------|-------------|--------------------------------|----------|------------------------------|
| `src`    | filename(s) | Inventory CSV file             | yes      | -                            |
| `prerun` | string      | Pre-run CLI Template to assign | no       | -                            |


### `type: onboard`

Trigger ZTP by factory-resetting the devices from the inventory CSV file. 

Currently, we only support ZTP for the VMs, by running the following CLI command:

```
execute factoryreset2 keepvmlicense
```

Supported arguments:

| Argument  | Values      | Description                | Required | Default |
|-----------|-------------|----------------------------|----------|---------|
| `src`     | filename(s) | Inventory CSV file         | no       | -       |
| `site`    | string      | Device name to trigger ZTP | no       | -       |
| `monitor` | boolean     | Monitor ZTP process        | no       | false   |
| `retry`   | boolean     | Attempt ZTP retry          | no       | false   |

The task logic is as follows:

- If an inventory file is specified (`src` argument), we will factory-reset all the devices in that file
- Else if a specific device is specified (`site` argument), we will factory-reset only that device
- Else if none of the arguments is specified, we will factory-reset all the tenant devices defined in the `config.yaml`

If ZTP monitoring is not requested (`monitor` argument), the task finishes immediately after the factory-reset. 
Otherwise, it will wait, periodically retrieving FMG tasks, looking for the Auto-Link tasks. When found, we will keep polling them, 
until they finish. We will print ZTP status for all the devices during this process, until it finishes. 

If one or more devices fail the Auto-Link process, we can attempt to reset the Auto-Link flag for the failed devices (`retry` argument), 
which should trigger another ZTP attempt. We will then monitor this attempt. We will not retry more than once. 