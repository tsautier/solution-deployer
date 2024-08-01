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
