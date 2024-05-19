# Script to query megaport cloud router (mcr) and grab bandwidth usage data
# Sends metrics to datadog for graphing
# Parts of script borrowed from scribd --- https://github.com/scribd/megaport-datadog/blob/master/lambda_function.py

from datadog import initialize, statsd, api
from statistics import mean
from pprint import pprint
import requests
import argparse
import time
import os

# You will typically want to set these as Environment vars
# You can use AWS Secrets Manager for these
parser = argparse.ArgumentParser()
parser.add_argument("-u", "--username", required=False, default=os.getenv("MP_USERNAME"), help="Megaport username")
parser.add_argument("-p", "--password", required=False, default=os.getenv("MP_PASSWORD"), help="Megaport password")
parser.add_argument("-k", "--key", required=False, default=os.getenv("DD_API_KEY"), help="DataDog API key")
parser.add_argument("-m", "--metric", required=False, default="megaport", help="DataDog Metric prefix e.g. megaport")
args = parser.parse_args()

# DataDog config and initialization
options = {
    "api_key": args.key
}

initialize(**options)


### Megaport Params
mp_url = "https://api.megaport.com/v2"
mp_auth_url = "https://auth-m2m.megaport.com/oauth2/token"
mp_auth_payload = 'grant_type=client_credentials'
mp_auth_headers = {'Content-Type': 'application/x-www-form-urlencoded'}

# Error handling for MP login
try:
    create_token_response = requests.request("POST", mp_auth_url, headers=mp_auth_headers, data=mp_auth_payload, auth=(args.username, args.password))
    login_token = create_token_response.json()['access_token']
except:
    print(create_token_response.text)
    exit(1)

## set headers for future MP requests
mp_headers = {'Authorization': f'Bearer {login_token}'}

## get list of all megaport products
try:
    list_response = requests.request("GET", mp_url+"/products", headers=mp_headers)
    list_response = list_response.json()
except:
    print(list_response.text)
    exit(1)

###############
# mcr_name = list_response['data'][0]['productName']
# mcr_uid = list_response['data'][0]['productUid']

products = list_response['data']

# Main dict that will hold all the metrics/data
product_metrics = {}

# Setting up the skeleton of products in the user's account
for p in products:
    product_metrics.update({p["productUid"]: {"product_name":p["productName"]}})

# print(product_metrics)

# Get current time in epoch milliseconds
epoch_current = int(time.time() * 1000)
# Gather sample data for the past 30 minutes
# epoch_to = epoch_current - 600000
epoch_to = epoch_current - 1800000

# Get bandwidth metrics for products
for u in product_metrics:
    # default tags we want to set
    product_name = "product_name:{}".format(product_metrics[u]["product_name"])
    product_uid = "product_uid:{}".format(u)
    custom_tags = ["source:megaport_datadog.py", product_name, product_uid]
    
    telemetry_response = requests.request("GET", "{mp_url}/product/mcr2/{product_uid}/telemetry?type=BITS&to={to_time}&from={from_time}".format(mp_url=mp_url, product_uid=u, to_time=epoch_current, from_time=epoch_to), headers=mp_headers)
    # print(telemetry_response)
    raw_data = telemetry_response.json()["data"]

    product_metrics[u].update({"raw_data": raw_data,
                            "mbps_in_samples": [],
                            "mbps_out_samples": []})

    # Get bits in/out with their timestamp
    for r in raw_data:
        if r["subtype"] == "In":
            for s in r["samples"]:
                # appending metrics so I can send multiple datapoints
                # https://docs.datadoghq.com/api/?lang=python#metrics
                product_metrics[u]["mbps_in_samples"].append((int(s[0]/1000), s[1]))
        elif r["subtype"] == "Out":
            for s in r["samples"]:
                    product_metrics[u]["mbps_out_samples"].append((int(s[0]/1000), s[1]))
        else:
            continue

        # Start sending our metrics to DataDog
        api.Metric.send(
            metric="{}.bandwidth.mbps_in".format(args.metric),
            points=product_metrics[u]["mbps_in_samples"],
            tags=custom_tags   
        )

        api.Metric.send(
            metric="{}.bandwidth.mbps_out".format(args.metric),
            points=product_metrics[u]["mbps_out_samples"],
            tags=custom_tags   
        )
# statsd.gauge("megaport.mcrtelemetry.inbound.mbps", mcr_in_mbps, tags=["env:prod", "team-name:network", "project:megaport", "task:mcr-telemetry", "type:inbound-usage-mbps"])
# # send mcr out bandwidth metrci
# statsd.gauge("megaport.mcrtelemetry.outbound.mbps", mcr_out_mbps, tags=["env:prod", "team-name:network", "project:megaport", "task:mcr-telemetry", "type:outbound-usage-mbps"])
