**Lamp Stacker Tutorial**

The following procedures help you deploy an Apache web server with PHP on your Amazon Ubuntu instance (sometimes called a LAMP web server or LAMP stack) using Stacker. You can use this server to host a static website or deploy a dynamic PHP application that reads and writes information to a database. We will be recreating the LAMP stack that can be find in [stacker_blueprints](https://github.com/remind101/stacker_blueprints). 

**Prerequisites:**

1. You must have the ***aws cli*** installed locally on your machine so that you are able to interface with AWS. If you don't have this configured check out: https://aws.amazon.com/cli/
2. Install Stacker: **pip install stacker**
3. Install stacker_blueprints: **pip install stacker_blueprints**

**Step 1: Create a VPC**

First, we will need to create a VPC to contain our EC2 Instance and RDS. To do this we can use the existing template found in the the [stacker_blueprints](https://github.com/remind101/stacker_blueprints) repo. 

1. We create a file called lamp.yaml and fill in all the variables that are defined in the [template file](https://github.com/remind101/stacker_blueprints/blob/master/stacker_blueprints/vpc.py) for a vpc stack. This file will act as our main configuration file and will contain the information that stacker needs to create the cloudformation template.
    ```
        stacks:
        # The name field allows you to define a name so that you can refer to the stack elsewhere
        # using the ${vpc::someParameter} 
          - name: vpc
            # The class_path refers to the location of the VPC template file. 
            class_path: stacker_blueprints.vpc.VPC
            variables:
              # Variables such as ${azcount} are defined in the env file
              AZCount: ${azcount}
              # Enough subnets for 4 AZs
              # InstanceType used for NAT instances
              InstanceType: ${nat_instance_type}
              SshKeyName: ${ssh_key_name}
              InternalDomain: internal
              # CidrBlock needs to be hold all of the Public & Private subnets above
              CidrBlock: 10.128.0.0/16
              ImageName: NAT
              PublicSubnets: 
                - 10.128.0.0/24
                - 10.128.1.0/24
                - 10.128.2.0/24
                - 10.128.3.0/24
              PrivateSubnets: 
                - 10.128.8.0/22
                - 10.128.12.0/22
                - 10.128.16.0/22
                - 10.128.20.0/22
    ```
    
2.  Next we create a file called lamp.env which will contain a set of variables that can be used inside the config, allowing us to slightly adjust configs based on which environment you are launching. 
    ```
    # namespace is a unique name that the stacks will be built under. This value
    # will be used to prefix the CloudFormation stack names as well as the s3
    # bucket that contains revisions of the stacker templates. This is the only
    # required environment variable.
    namespace: my-lamp-stack
    
    # VPC settings
    azcount: 2
    nat_instance_type: m3.medium
    ssh_key_name: your_ssh_key
    ```

3. In order to deploy the vpc that you created simply run stacker build and log into your aws console. Stacker uses your environment variables to decide where to deploy the created cloudformation template.
    ```
    stacker build ./lamp.yaml ./lamp.env
    ```

**Step 2: Configurations Hooks**

In the stacker template above, we require an ssh_key_name for the VPC. Using Stacker hooks when can ensure that the ${ssh_key_name} provided is actually valid and if it is not we can create or import a valid key. We would do this by adding the following to the top of the lamp.yaml file.
```
# Hooks require a path.
# If the build should stop when a hook fails, set required to true.
# pre_build happens before the build
# post_build happens after the build
pre_build:
  - path: stacker.hooks.route53.create_domain
    required: true
    # Additional args can be passed as a dict of key/value pairs in kwargs
    args:
      domain: ${external_domain}
# post_build:
```

 We can add a variety of pre_build and post_build hooks to our configuration which would simplify our workflow, but in this tutorial this is the only hook we will use. You can see a list of the other hooks that stacker has at: http://stacker.readthedocs.io/en/latest/api/stacker.hooks.html#
    
Now when we run:
```
stacker build ./lamp.yaml ./lamp.env
```
 it will ask us if we want to create or import a new key if the key name we provide is not valid.

***Step 3: Create a MySQL RDS***

1. In order to create the configuration file for a Mysql RDS instance we need to specify what VPC it belongs to and what subnets it resides  in. In order to do this we need to introduce the notion of lookups, the most common lookup is the output lookup which allows us to reference parameters in other stacks. For example, if we wanted to access the VpcId in our RDS instance, we would write:
    ```
    ${output name_of_vpc_stack::VpcId}
    ```
    In the lamp.yaml file we simply named our vpc stack, vpc, so we would be able to write this lookup as:
    
    ```
    ${output vpc::VpcId}
    ```
    
    There are many other lookups that stacker is able to do and we will be using some of them later in this tutorial. If you want to see a comprehensive list of all the lookups that are in Stacker go to: http://stacker.readthedocs.io/en/latest/lookups.html 
    
2.  Now we add the new configuration of our RDS to our lamp.yaml file.
    ```
      - name: mysqlMaster
        class_path: stacker_blueprints.rds.mysql.MasterInstance
        variables:
          Subnets: ${output vpc::PrivateSubnets}
          InstanceType: ${db_instance_type}
          AllowMajorVersionUpgrade: "false"
          AutoMinorVersionUpgrade: "false"
          AllocatedStorage: ${storage_size}
          IOPS: ${iops}
          InternalZoneName: ${output vpc::InternalZoneName}
          InternalZoneId: ${output vpc::InternalZoneId}
          InternalHostname: ${master_name}
          DBInstanceIdentifier: ${master_name}
          DBFamily: ${db_family}
          EngineVersion: ${engine_version}
          EngineMajorVersion: ${engine_major_version}
          StorageEncrypted: ${master_storage_encrypted}
          # MasterInstance specific
          MasterUser: ${db_user}
          MasterUserPassword: ${db_passwd}
          DatabaseName: ${db_name}
          MultiAZ: "false"
          VpcId: ${output vpc::VpcId}
          DefaultSG: ${output vpc::DefaultSG}
          PublicSubnets: ${output vpc::PublicSubnets}
          PrivateSubnets: ${output vpc::PrivateSubnets}
          AvailabilityZones: ${output vpc::AvailabilityZones}
    ```
3. Next, we add the database specific fields to our lamp.env file. 
    ```
    # MYSQL Settings
    db_instance_type: db.m3.large
    storage_size: 100
    iops: 1000
    db_family: mysql5.6
    engine_version: 5.6.23
    engine_major_version: "5.6"
    storage_encrypted: "true"
    
    # DATABASE Settings
    master_name: mysql-master
    db_user: myuser
    db_passwd: SECRETPASSWORD
    db_name: mydb
    master_storage_encrypted: "true"
    ```
4. Finally, we update our stack on cloudformation using stacker.
    ```
    stacker build ./lamp.yaml ./lamp.env
    ```
    

***Step 4: Create a EC2 Instance***

***Step 5: Configure our EC2 Instance***

***Step 6: Gotcha's and warnings***
    



    

    
    

