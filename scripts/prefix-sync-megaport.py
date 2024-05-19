''' This script is used to sync the prefix list filters on the Megaport MCR
Can be used in DRY-RUN mode to test the changes before applying them to the MCR
'''
import argparse
import requests
import logging
import warnings
import os
import yaml
import json
# ignore warnings during testing
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Function to get initial arguments from user


def get_initial_args():
    '''
        Get initial arguments from user such as MCR ID, Prefix Lists to Sync and DRY-RUN mode
    '''
    try:
        # Load default values from YAML file
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Append the relative path to the YAML file
        yaml_file_path = os.path.join(script_dir, 'params.yml')
        with open(yaml_file_path, 'r') as f:
            defaults = yaml.safe_load(f)

        parser = argparse.ArgumentParser("Parameters for the script")
        parser.add_argument(
            "-m", "--mcr_id", help="The Megaport MCR ID", default=os.environ.get('MCR_ID', defaults['mcr_id']))
        parser.add_argument(
            "-d", "--dry_run", help="Dry Run (no changes to be made): true or false", default=os.environ.get('DRY_RUN', defaults['dry_run']))
        parser.add_argument(
            "-p", "--prefix_list_map", help="List of Megaport Prefix List Names to Sync Up (comma separated): aws,gcp,azure",
            default=os.environ.get('PREFIX_LISTS', defaults['megaport_prefix_lists_map']))
        parser.add_argument(
            "-t", "--megaport_token_url", help="Megaport TOKEN URL",
            default=os.environ.get('MEGAPORT_TOKEN_URL', defaults['megaport_token_url']))
        parser.add_argument(
            "-u", "--megaport_api_url", help="Megaport API URL",
            default=os.environ.get('MEGAPORT_API_URL', defaults['megaport_api_url']))
        parser.add_argument(
            "-k", "--megaport_key", help="Megaport API Secret Key",
            default=os.environ.get('MEGAPORT_KEY', defaults['megaport_key']))
        args = parser.parse_args()

        # Sanity Check User Input or Env Variables
        if args.mcr_id is None or args.dry_run is None or args.prefix_list_map is None or args.megaport_token_url is None or args.megaport_key is None:
            logging.error(
                "Parameter or environment variable is not set", e)
            exit(1)
        if args.dry_run not in ["true", "false"]:
            logging.error(
                "Invalid value for dry_run: {}. Must be TRUE or FALSE.".format(args.dry_run))
            exit(1)
        logging.info(
            "Arguments parsed successfully. MCR ID: {} | Dry Run?: {} | Prefix List Map: {} | Megaport Token URL: {}".format(args.mcr_id, args.dry_run, args.prefix_list_map, args.megaport_token_url))
        return {'mcr_id': args.mcr_id, 'dry_run': args.dry_run,
                'prefix_list_map': args.prefix_list_map, 'megaport_token_url': args.megaport_token_url,
                'megaport_key': args.megaport_key, 'megaport_api_url': args.megaport_api_url}

    except Exception as e:
        logging.error("Error parsing arguments: ", e)
        exit(1)


def megaport_get_token(url, basic_auth) -> str:
    '''
    Get token from Megaport API
    '''
    try:
        payload = 'grant_type=client_credentials'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {basic_auth}'
        }

        response = requests.request(
            "POST", url, headers=headers, data=payload).json()
        logging.info("Got Megaport Token via API")
        return response['access_token']
    except Exception as e:
        logging.error("Error Getting Megaport Token via API: ", e)
        exit(1)


def megaport_get_all_prefix_lists(url, token, mcr_id):
    '''
    Get All Prefix Lists in MCR from Megaport API
    '''
    try:
        url = f'{url}/product/mcr2/{mcr_id}/prefixLists'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        payload = {}
        all_prefix_lists = requests.request(
            "GET", url, headers=headers, data=payload).json()
        logging.info("Got Megaport Prefix Lists")
        return all_prefix_lists['data']

    except Exception as e:
        logging.error("Error Getting Megaport Prefix Lists: ", e)
        exit(1)


def desired_prefixes_to_be_installed(file_path):
    '''
    Read file as json and return desired prefixes to be installed
    '''
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            desired_subnet_list = []
            for key in data.keys():
                for subnet in data[key]:
                    desired_subnet_list.append(subnet['subnet'])
            logging.info(
                "Read in JSON File and Returned Desired Subnets: {}".format(file_path))
            return desired_subnet_list
    except Exception as e:
        logging.error("Error Reading JSON File: ", e)
        exit(1)


def flatten_list(matrix):
    '''Flatten a 2D list'''
    flat_list = []
    for row in matrix:
        flat_list += row
    return flat_list


def megaport_get_prefix_list_routes(url, token, mcr_id, prefix_id):
    '''
    Get prefix routes from Megaport API
    '''
    try:
        current_prefix_list = []
        url = f'{url}/product/mcr2/{mcr_id}/prefixList/{prefix_id}'
        payload = {}
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }

        current_prefix_data = requests.request(
            "GET", url, headers=headers, data=payload).json()
        for subnet in current_prefix_data['data']['entries']:
            current_prefix_list.append(subnet['prefix'])
        logging.info(
            f'Got Prefix List Routes from Megaport API | Prefix ID: {prefix_id}')
        return current_prefix_list

    except Exception as e:
        logging.error("Error Getting Megaport Prefix Lists: ", e)
        exit(1)


def megaport_update_prefix_list(url, token, mcr_id, prefix_id, list_name, desired_routes):
    '''
    Update prefix list in Megaport API
    '''
    try:
        url = f'{url}/product/mcr2/{mcr_id}/prefixList/{prefix_id}'
        entries = []
        for route in desired_routes:
            entries.append({"action": "permit", "prefix": route})
        payload = json.dumps(
            {"description": list_name, "addressFamily": "IPv4", "entries": entries})
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        response = requests.request(
            "PUT", url, headers=headers, data=payload)
        logging.info(
            f'Updated Prefix List Routes in Megaport API | Prefix ID: {prefix_id} | response: {response.status_code} |\n Payload: {json.dumps(response.json(), indent=4)}')
        if response.status_code != 200:
            raise Exception(
                "Unexpected Response: --> ".format(response.status_code))
        return response
    except Exception as e:
        logging.error("Error Updating Megaport Prefix Lists: ", e)
        exit(1)


if __name__ == "__main__":

    # Get Script Path
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Get initial arguments from user
    initial_args = get_initial_args()

    # Get Megaport Token
    megaport_token = megaport_get_token(
        initial_args['megaport_token_url'], initial_args['megaport_key'])

    # Get All MP Prefix Lists
    all_megaport_prefix_lists = megaport_get_all_prefix_lists(
        initial_args['megaport_api_url'], megaport_token, initial_args['mcr_id'])

    # Map MP Prefix List Names to IDs
    pl_name_to_id = {}
    for prefix_list in all_megaport_prefix_lists:
        pl_name_to_id[prefix_list['description']] = prefix_list['id']

    # Plan Changes to be Made
    changes_to_be_made = {}

    for name, pl in initial_args['prefix_list_map'].items():
        desired_subnet_list = []

        for item in pl:
            json_file_path = os.path.join(script_dir, '../terraform/',f'subnets/{item}')
            desired_subnet_list.append(
                desired_prefixes_to_be_installed(json_file_path))

        flattened_desired_list = flatten_list(desired_subnet_list)
        current_prefix_list = megaport_get_prefix_list_routes(
            initial_args['megaport_api_url'], megaport_token, initial_args['mcr_id'], pl_name_to_id[name])

        set_diff_add = set(flattened_desired_list) - set(current_prefix_list)
        set_diff_del = set(current_prefix_list) - set(flattened_desired_list)

        changes_to_be_made[name] = {'routes_to_add': list(set_diff_add),
                                    'routes_to_delete': list(set_diff_del),
                                    'current': current_prefix_list,
                                    'desired': flattened_desired_list,
                                    'prefix_id': pl_name_to_id[name],
                                    'description': name}

        if len(set_diff_add) > 0 or len(set_diff_del) > 0:
            logging.info(
                f'Changes Detected For {name} |\n {json.dumps(changes_to_be_made[name], indent=4)}')
        else:
            logging.info(
                f'No Changes Detected For {name}')

    # Execute Changes
    if initial_args['dry_run'] == "false":
        for prefix_list in changes_to_be_made:
            if len(changes_to_be_made[prefix_list]['routes_to_add']) == 0 and len(changes_to_be_made[prefix_list]['routes_to_delete']) == 0:
                continue
            megaport_update_prefix_list(
                initial_args['megaport_api_url'],
                megaport_token, initial_args['mcr_id'],
                changes_to_be_made[prefix_list]['prefix_id'],
                changes_to_be_made[prefix_list]['description'],
                changes_to_be_made[prefix_list]['desired'])
