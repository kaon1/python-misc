import json
import requests
import logging
import warnings
import sys
from datadog import initialize, statsd
warnings.filterwarnings('ignore')

def create_megaport_session():
    '''Create a session with Megaport API and return the access token.'''
    mp_auth_url = "https://auth-m2m.megaport.com/oauth2/token"
    mp_auth_payload = 'grant_type=client_credentials'
    mp_auth_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    username = ""
    password = ""

    # Error handling for MP login
    try:
        create_token_response = requests.request("POST", mp_auth_url, headers=mp_auth_headers, data=mp_auth_payload, auth=(username, password), timeout=5)
        logging.info("Megaport login response: %s", create_token_response.status_code)
        return create_token_response.json()['access_token']
    except requests.exceptions.RequestException as e:
        logging.error("Error: %s", e)
        sys.exit(1)

def megaport_get_something(mp_url, mp_query, login_token):
    '''Get something from Megaport API.'''

    ## set headers for future MP requests
    mp_headers = {'Authorization': f'Bearer {login_token}'}

    try:
        mp_response = requests.request("GET", mp_url + mp_query, headers=mp_headers, timeout=5)
        logging.info("Megaport GET Request: %s and Response: %s", mp_query, mp_response.status_code)
        return mp_response.json()
    except requests.exceptions.RequestException as e:
        logging.error("Error: %s", e)
        sys.exit(1)


def main():

    # Setup logging
    logging.basicConfig(filename='./megaport-status.log', level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    try:
        # Datadog API Key
        dd_api_key = "get-from-secure-resource"
        # Set DD options for statsd init
        options = {
            'statsd_host': '127.0.0.1',
            'statsd_port': 8125,
            'api_key': dd_api_key
        }
        initialize(**options)
        logging.info("Datadog initialized successfully")
    except Exception as e:
        logging.error("Error initializing Datadog: %s", e)
        sys.exit(1)

    login_token = create_megaport_session()
    data = megaport_get_something("https://api.megaport.com/v2", "/products?provisioningStatus=LIVE", login_token)
    
    resource_list = []

    for mcr in data["data"]:
        if mcr.get("provisioningStatus") == 'LIVE':
            mcr_status = "0"
        else:
            mcr_status = "2"
        resource_list.append({"name": mcr.get("productName"), "status": mcr_status, "productType": mcr.get("productType"), "location": mcr["locationDetail"].get("name"), "parent": "root"})
        logging.info("Logging MCR: %s", mcr.get("productName"))
        for vxc in mcr["associatedVxcs"]:
            if vxc.get("provisioningStatus") == 'LIVE':
                vxc_status = "0"
            else:
                vxc_status = "2"
            resource_list.append({"name": vxc.get("productName"), "status": vxc_status, "productType": vxc.get("productType"), "up": vxc.get("up"), "parent": vxc["aEnd"].get("productName"), "location": mcr["locationDetail"].get("name")})
            logging.info("Logging VXC: %s", vxc.get("productName"))
            cspPeer = vxc['resources']['csp_connection'][0]
            bgpPeerip = cspPeer['bgp_peers'][0]
            if cspPeer['bgp_status'][bgpPeerip] == 1:
                bgpPeerStatus = "0"
            else:
                bgpPeerStatus = "2"
            resource_list.append({"name": cspPeer['bgp_peers'][0], "productType": "bgpPeer", "parent": vxc.get("productName"), "status": bgpPeerStatus, "location": mcr["locationDetail"].get("name")})
            logging.info("Logging BGP Peer: %s", cspPeer['bgp_peers'][0])
    for resource in resource_list:
        statsd.service_check(
            check_name="networking.megaport.service_check.resource_status",
            status=resource["status"],
            message=resource["name"],
            hostname="networking_megaport_poller",
            tags=["env:prd", "app:megaport_service_checks",
                    "megaport_resource_name:"+resource.get('name'), "megaport_resource_type:"+resource.get('productType'), "parent:"+resource.get('parent'), "location:"+resource.get('location'), "team-name:networking"]
        )
        logging.info("Service Check sent to Datadog: %s", resource_list)

if __name__ == "__main__":
    main()
