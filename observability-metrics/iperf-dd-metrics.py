# Script to run iperf3 test to measure bandwidth to remote site.
# Runs in reverse mode to measure both ingress and egress bandwidth
# Sends avg bandwidth metric to Datadog as a custom gauge metric
# Its suggested you run this script as a cron job on a regular hourly interval
# Kaon Thana 6-16-2021

from datadog import initialize, statsd
import time
import iperf3
import os

# Set vars
# Remote iperf server IP
remote_site = os.getenv('REMOTE_SITE_IP')
# Datadog API Key
api_key = os.getenv('DD_API_KEY')
# How long to run iperf3 test in seconds
test_duration = 20

# Set DD options for statsd init
options = {
    'statsd_host': '127.0.0.1',
    'statsd_port': 8125,
    'api_key': api_key
}
initialize(**options)

# Set Iperf Client Options
# Run 10 parallel streams on port 5201 for duration w/ reverse
client = iperf3.Client()
client.server_hostname = remote_site
client.zerocopy = True
client.verbose = False
client.reverse = True
client.port = 5201
client.num_streams = 10
client.duration = int(test_duration)
client.bandwidth = 1000000000

# Run iperf3 test
result = client.run()

# extract relevant data
sent_mbps = int(result.sent_Mbps)
received_mbps = int(result.received_Mbps)
#retransmits = result.retransmits

# send Metrics to DD and add some tags for classification in DD GUI
# send bandwidth metric - egress mbps
statsd.gauge('iperf3.test.mbps.egress', sent_mbps, tags=["team_name:your_team", "team_app:iperf"])
# send bandwidth metric - ingress mbps
statsd.gauge('iperf3.test.mbps.ingress', received_mbps, tags=["team_name:your_team", "team_app:iperf"])