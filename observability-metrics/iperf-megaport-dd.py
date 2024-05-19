# Script to run iperf3 test to measure bandwidth to remote site.
# Sends avg bandwidth metric to Datadog as a custom gauge metric
# Its suggested you run this script as a cron job on a regular hourly interval
# Kaon Thana 6-08-2023

# Example way to run script
# python3 iperf-megaport-dd.py --direction upload --dest_name gcpuseast1 --dest_ip 10.X.X.X --dest_port 5201 --numofstreams 1 --duration 10 --bandwidth 1000000000
# output is sent to datadog, find via metrics explorer by searching 'iperf3'

from datadog import initialize, statsd
import time
import iperf3
import os
import argparse

### Parse Command Line Keyword Arguments
parser = argparse.ArgumentParser()
parser.add_argument('--direction')
parser.add_argument('--dest_name')
parser.add_argument('--dest_ip')
parser.add_argument('--dest_port')
parser.add_argument('--numofstreams')
parser.add_argument('--duration')
parser.add_argument('--bandwidth')

args = parser.parse_args()

argument_dict = {'direction': args.direction, 'dest_name': args.dest_name, 'dest_port': args.dest_port, 'numofstreams': args.numofstreams, 'duration': args.duration, 'dest_ip': args.dest_ip, 'bandwidth': args.bandwidth}
   
# Set vars
# Datadog API Key
api_key = os.getenv('DD_API_KEY')

# Set DD options for statsd init
options = {
    'statsd_host': '127.0.0.1',
    'statsd_port': 8125,
    'api_key': api_key
}
initialize(**options)

# Set Iperf Client Options
client = iperf3.Client()
client.server_hostname = argument_dict['dest_ip']
client.zerocopy = True
client.verbose = False
client.reverse = False
client.port = argument_dict['dest_port']
client.num_streams = int(argument_dict['numofstreams'])
client.duration = int(argument_dict['duration'])
client.bandwidth = int(argument_dict['bandwidth'])

# Run iperf3 test
perf_result = client.run()

# print(test_result)
# print(int(test_result.received_Mbps))
# print(int(test_result.retransmits))

# extract relevant data
received_mbps = int(perf_result.received_Mbps)
retransmits = int(perf_result.retransmits)

## send Metrics to DD and add some tags for classification in DD GUI
# send received bandwidth metric
statsd.gauge("iperf3."+ argument_dict['dest_name'] + "." + argument_dict['direction'] +"."+ argument_dict['dest_port'] + "." + "speedtest", received_mbps, tags=["env:prod", "team-name:network", "project:megaport", "task:connectivity-testing", "type:speedtest"])
# send retransmit count
statsd.gauge("iperf3."+ argument_dict['dest_name'] + "." + argument_dict['direction'] +"."+ argument_dict['dest_port'] + "." + "retransmits", retransmits, tags=["env:prod", "team-name:network", "project:megaport", "task:connectivity-testing", "type:retransmits"])
