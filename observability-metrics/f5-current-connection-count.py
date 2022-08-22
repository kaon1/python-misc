# This app uses the F5 API to load information about the BigIP system connections
# We then send # of total system connections to Datadog as a metric
# Kaon Thana 6-17-2021

import requests
from requests.auth import HTTPBasicAuth
from datadog import initialize, statsd
import os
#from nested_lookup import nested_lookup
#import time

# For Auth to BIG-IP
# This should be changed in the future to something more secure
f = open("somefilepw.txt", "r")
lines = f.readlines()
username = lines[0].rstrip()
password = lines[1].rstrip()
f.close()

# Set vars
# BigIP Host
host = "hostip"
# Datadog API Key
api_key = os.getenv('DD_API_KEY')

# Set DD options for statsd init
options = {
    'statsd_host': '127.0.0.1',
    'statsd_port': 8125,
    'api_key': api_key
}
initialize(**options)

# F5 iControl API - Get URL to access stats. Use Basic Auth
virtual_stats_url = 'https://' + host +'/mgmt/tm/ltm/virtual/stats'
virtual_stats_response = requests.get(virtual_stats_url, verify=False, auth=HTTPBasicAuth(username, password))

# convert requests response to json
virtual_stats_json = virtual_stats_response.json()

# set cur_conns var to 0
cur_conns = 0

# loop through virtual address servers one by one and get all current connections
# Count all and add to cur_conns
for member in virtual_stats_json['entries']:
    cur_conns += virtual_stats_json['entries'][member]['nestedStats']['entries']['clientside.curConns']['value']
#    cur_conns += virtual_stats_json['entries'][member]['nestedStats']['entries']['ephemeral.curConns']['value']

# get Client SSL VPN Conenctions on dtls udp port 10000
dtls_udp_conns = virtual_stats_json['entries']['https://localhost/mgmt/tm/ltm/virtual/<server_name>/stats']['nestedStats']['entries']['clientside.curConns']['value']
# get Client SSL VPN Conenctions on port 443
ssl_tcp_conns = virtual_stats_json['entries']['https://localhost/mgmt/tm/ltm/virtual/<server_name>/stats']['nestedStats']['entries']['clientside.curConns']['value']

# send Metrics to DD and add some tags for classification in DD GUI
# send sys connection count metric
statsd.gauge('f5metrics.site1.hostname1.sys.connections.count', cur_conns, tags=["env:prd", "app:f5metrics", "site:site1", "device:hostname1"])
statsd.gauge('f5metrics.site1.hostname1.dtls.udp.conns', dtls_udp_conns, tags=["env:prd", "app:f5metrics", "site:site1", "device:hostname1"])
statsd.gauge('f5metrics.site1.hostname1.ssl.tcp.conns', ssl_tcp_conns, tags=["env:prd", "app:f5metrics", "site:site1", "device:hostname1"])
