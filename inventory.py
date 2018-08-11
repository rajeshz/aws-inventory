# Python imports
import boto3
from botocore.exceptions import *
import botocore
import collections
import csv
import json

import smtplib
import os, hmac, hashlib, sys
import pprint
import logging
from sys import exit
import time

import res.utils as utils
import config

# AWS Services imports 
import res.glob    as glob
import res.compute as compute
import res.storage as storage
import res.db      as db
import res.iam     as iam
import res.network as net
import res.fact    as fact

#
# Let's rock'n roll
#

# --- AWS basic information
ownerId = utils.get_ownerID()
config.logger.info('OWNER ID:'+ownerId)


# --- AWS Regions 
with open('aws_regions.json') as json_file:
    aws_regions = json.load(json_file)
regions = aws_regions.get('Regions',[] ) 


# Initialization
inventory = {}

# Argumentation
nb_arg = len(sys.argv) - 1
if (nb_arg == 0):
    arguments = config.SUPPORTED_COMMANDS
    nb_arg = len(arguments)
else:
    arguments = sys.argv[1:]
    utils.check_arguments(arguments)
print('-'*100)
print ('Number of arguments:', nb_arg, 'arguments.')
print ('Argument List:', str(arguments))
print('-'*100)

# 
# ----------------- EC2
#

if ('ec2' in arguments):
    ec2_inventory        = []
    interfaces_inventory = []
    vpcs_inventory       = []
    ebs_inventory        = []

    # Lookup in every AWS Region
    for current_region in regions:
    
        current_region_name = current_region['RegionName']
        utils.display(ownerId, current_region_name, "ec2 inventory")

        # EC2 instances
        instances = compute.get_ec2_inventory(current_region_name)
        for instance in instances:
            json_ec2_desc = json.loads(utils.json_datetime_converter(instance))
            ec2_inventory.append(compute.get_ec2_analysis(json_ec2_desc, current_region_name))

        # Network
        for ifc in compute.get_interfaces_inventory(current_region_name):
            interfaces_inventory.append(json.loads(utils.json_datetime_converter(ifc)))

        # VPCs
        for vpc in compute.get_vpc_inventory(current_region_name):
            vpcs_inventory.append(vpc)

        # EBS
        ebs_list = compute.get_ebs_inventory(current_region_name)
        for ebs in ebs_list:
            ebs_inventory.append(json.loads(utils.json_datetime_converter(ebs)))

        # EBS, snapshot
        # describe_nat_gateways()
        # describe_internet_gateways()
        # describe_reserved_instances()
        # describe_snapshots()
        # describe_subnets()

    inventory["ec2"]            = ec2_inventory
    inventory["ec2-interfaces"] = interfaces_inventory
    inventory["ec2-vpcs"]       = vpcs_inventory
    inventory["ec2-ebs"]        = ebs_inventory


# 
# ----------------- Lambda functions
#
if ('lambda' in arguments):
    inventory["lambda"] = compute.get_lambda_inventory(ownerId)


# 
# ----------------- Lighstail instances
#
if ('lightsail' in arguments):
    utils.display(ownerId, "all regions", "lightsail inventory")
    inventory['lightsail'] = json.loads(utils.json_datetime_converter(compute.get_lightsail_inventory()))


#
# ----------------- EFS inventory
#
if ('efs' in arguments):
    inventory['efs'] = storage.get_efs_inventory(ownerId)


#
# ----------------- Glacier inventory
#
if ('glacier' in arguments):
    inventory['glacier'] = storage.get_glacier_inventory(ownerId)


#
# ----------------- RDS inventory
#
if ('rds' in arguments):
    inventory['rds'] = db.get_rds_inventory(ownerId)


#
# ----------------- dynamodb inventory
#
if ('dynamodb' in arguments):
    inventory['dynamodb'] = db.get_dynamodb_inventory(ownerId)


#
# ----------------- KMS inventory
#
if ('kms' in arguments):
    inventory['kms'] = iam.get_kms_inventory(ownerId)


#
# ----------------- API Gateway inventory
#
if ('apigateway' in arguments):
    inventory['apigateway'] = net.get_apigateway_inventory(ownerId)


#
# ----------------- Cost Explorer (experimental)
#
if ('ce' in arguments):
    ce_inventory = []
    utils.display(ownerId, 'global', "cost explorer inventory")
    list_ce = fact.get_ce_inventory(ownerId, None).get('ResultsByTime')
    for item in list_ce:
        ce_inventory.append(json.loads(utils.json_datetime_converter(item)))
    print(ce_inventory)
    inventory['cost-explorer'] = ce_inventory

#
# ----------------- EKS inventory (Kubernetes) : not implemented yet in AWS CLI
#
#for current_region in regions:
#    current_region_name = current_region['RegionName']
#    eks_list = eks.get_eks_inventory(ownerId, current_region_name)
#    #print(eks_list)
# Other non implemented services:
#  - alexaforbusiness


#
# International Resources (no region)
#

region_name = 'global'

#
# ----------------- S3 quick inventory
#
if ('s3' in arguments):
    inventory["s3"] = storage.get_s3_inventory(ownerId, region_name)

#
# ----------------- Final inventory
#

filename_json = 'AWS_{}_{}.json'.format(ownerId, config.timestamp)
try:
    json_file = open(config.filepath+filename_json,'w+')
except IOError as e:
    config.logger.error("I/O error({0}): {1}".format(e.errno, e.strerror))

json_file.write(json.JSONEncoder().encode(inventory))

#
# EOF
#
json_file.close()

