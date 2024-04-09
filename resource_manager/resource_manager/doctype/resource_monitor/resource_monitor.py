from datetime import datetime
import psutil
import json
import subprocess
import frappe
import json
import os
# Copyright (c) 2024, nutan and contributors
# For license information, please see license.txt
from frappe.model.document import Document

class ResourceMonitor(Document):
    pass

def push_on_infra_dash_pipe(site_health_data):
    print(site_health_data)
    site_health_data['doctype'] = 'Resource Monitor'
    new_doc = frappe.get_doc(site_health_data)
    new_doc.insert()
    return "200"

def main():
    """
    The main function called every 5 minutes (set in hooks.py).
    It retrieves the site list, collects data for each site, and pushes the data to the infra dashboard.
    """
    site_list = get_sites_list()
    site_data = []
    for site in site_list:
        directory_path = get_site_path(site)
        if directory_path:
            site_health_data = collect_sites_data(directory_path)
            site_health_data["server_information"] = site
            site_health_data["db_name"] = get_database_name(directory_path)
            if is_running_in_docker():
                # get docker detail and add in server health
                site_health_data["docker_container"] = str(server_name())
                site_health_data["is_docker"] = "1"
            else:
                site_health_data["disk_io"] = str(disk_io())
                site_health_data["net_io"] = str(net_io())
            
            # get server details and add
            # site_health_data["server_information"] = str(server_name())
            site_health_data["disk_usage"] = str(disk_usage())
            site_health_data["memory_usage"] = str(memory_consumption())
            site_health_data["date_time"] = str(get_current_datetime())
            # site_health_data["nginx_status"] = nginx_status()
            # site_health_data["mysql_status"] = mysql_status()
            site_health_data["cpu_usage"] = str(cpu_utilization())
            push_on_infra_dash_pipe(site_health_data)
            return "200"
    return "200"

def get_database_name(site_path):
    """
    Get the database name for a site from its site_config.json file.
    """
    config_file_path = os.path.join(site_path, "site_config.json")
    with open(config_file_path, "r") as config_file:
        site_config_data = json.loads(config_file.read())
        return site_config_data.get("db_name", "not available")

def get_current_datetime():
    """
    Get the current date and time as a formatted string.
    """
    current_datetime = datetime.now()
    current_datetime_str = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
    return current_datetime_str

def get_site_path(site):
    """
    Build the complete path for the current site directory.
    """
    root_directory = '/'
    directory_name = site
    for root, dirs, files in os.walk(root_directory):
        if directory_name in dirs:
            return os.path.join(root, directory_name)
    return ""

def get_sites_list():
    """
    Get the list of sites on the current Frappe bench.
    """
    command = "bench --site all list-apps --format json"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    sites = dict(data)
    site_list = list(sites.keys())
    return site_list

def collect_sites_data(site_name):
    """
    Collect data for the given site, including site size and number of Gunicorn processes.
    """
    site_health_data = {}
    site_health_data["site_size"] = str(get_site_size(site_name))
    site_health_data["gunicorn_processes"] = str(get_gunicorn_process())
    site_health_data["date_time"] = get_current_datetime()
    site_health_data["is_bench_site"] = 1
    return site_health_data

def get_site_size(site_name):
    """
    Get the size of the directory for the given site.
    """
    command = f"du -sh --apparent-size {site_name}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    site_size = result.stdout.strip().split("\t")[0]
    return site_size

def get_gunicorn_process():
    """
    Get the count of Gunicorn workers.
    """
    command = "ps -eaf | grep gunicorn"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    gunicorn_processes = result.stdout.strip()
    if "-w" in gunicorn_processes:
        gunicorn_processes = gunicorn_processes.split("-w", 1)[1].split()[0]
    else:
        gunicorn_processes = ""
    return gunicorn_processes



    

def server_name():
    """
    Retrieves the server name.
    Returns the server name as a string.
    """
    return subprocess.check_output(['hostname']).decode('utf-8')

def is_running_in_docker():
    """
    Checks if the script is running inside a Docker container.
    Returns True if running inside a Docker container, False otherwise.
    """
    if os.path.exists('/.dockerenv'):
        return True

    with open('/proc/self/cgroup', 'rt') as f:
        for line in f:
            if 'docker' in line:
                return True
    return False

def get_current_datetime():
    """
    Retrieves the current datetime.
    Returns the current datetime as a string in the format '%Y-%m-%d %H:%M:%S'.
    """
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def cpu_utilization():
    """
    Retrieves the CPU utilization.
    Returns the CPU utilization as a float.
    """
    return psutil.cpu_percent()

def memory_consumption():
    """
    Retrieves the memory consumption.
    Returns the memory consumption as a float.
    """
    return psutil.virtual_memory().percent

def server_load():
    """
    Retrieves the server load average.
    Returns a list of load average values.
    """
    try:
        cpu_cores = float(os.cpu_count())
        load_per_core = float(100/cpu_cores)
        load_average = float(os.getloadavg()[1]*load_per_core)
        return load_average
    except:
        return ""

def disk_usage():
    """
    Retrieves the disk usage.
    Returns the disk usage as a float.
    """
    return psutil.disk_usage('/').percent

def post_to_infra_dash(payload):
    """
    Sends the payload to the server health dashboard.
    Returns True if the request is successful, False otherwise.
    """
    url = g_site_health_data_url
    headers = {"Authorization": g_authorization}
    response = requests.post(url, headers = headers, data = json.dumps(payload))
    if str(response.status_code) == str(200):
        return True
    else:
        return False

def push_on_infra_pipe(payload):
    print(payload)

def mysql_status():
    """
    Checks the status of the MySQL service.
    Returns "Active" if the service is active, "Not Active" if it's not active, 
    or "Error" if an error occurs.
    """
    try:
        output = subprocess.check_output(
            ['sudo', 'service', 'mysql', 'status']).decode('utf-8')
        # Check if the MySQL service is active
        if 'Active: active (running)' in output:
            return "Active"
        else:
            return "Not Active"
    except:
        return "Error"

def nginx_status():
    """
    Checks the status of the Nginx service.
    Returns "Active" if the service is active, "Not Active" if it's not active, 
    or "Error" if an error occurs.
    """
    try:
        output = subprocess.check_output(
            ['sudo', 'service', 'nginx', 'status']).decode('utf-8')
        # Check if the Nginx service is active
        if 'running' in output:
            return "Active"
        else:
            return "Not Active"
    except:
        return "Error"

def uptime():
    """
    Retrieves the system uptime.
    Returns the system uptime as a string.
    """
    return subprocess.check_output(['uptime']).decode('utf-8')



def net_io():
    """
    Retrieves the network I/O statistics.
    Returns the network I/O statistics as a named tuple.
    """
    return psutil.net_io_counters()

def disk_io():
    """
    Retrieves the disk I/O statistics.
    Returns the disk I/O statistics as a named tuple.
    """
    return psutil.disk_io_counters()

def delete_week_old_data():
    week_old = frappe.utils.add_to_date(frappe.utils.now_datetime(), weeks=-1)
    frappe.db.delete('Resource Monitor', {"creation":("<", week_old)})