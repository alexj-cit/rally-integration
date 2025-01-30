import requests
import pytz
from datetime import datetime, timedelta

RALLY_URL = 'https://rally1.rallydev.com/slm/webservice/1.29/subscription.js?fetch=Workspaces,Projects,Name&pretty=true'

RALLY_STORIES = 'https://rally1.rallydev.com/slm/webservice/v2.0/hierarchicalrequirement?query=' \
                '(Project.ObjectID = :project_id)&start=:start_index&pagesize=:page_size'

RALLY_DEFECTS = 'https://rally1.rallydev.com/slm/webservice/v2.0/defects?query=' \
                '(Project.ObjectID = :project_id)&start=:start_index&pagesize=:page_size'

headers = {
    # 'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json',
    'zsessionid': '_B7WrOkAPSPavaK4xq2CUqtCfCesR0b7reJXKHxrdec'
}


def get_project():
    response = requests.get(RALLY_URL, headers=headers)
    if response.status_code == 200:
        workspaces = response.json()['Subscription']['Workspaces']
        projects_list = []
        for workspace in workspaces:
            projects = workspace['Projects']
            for project in projects:
                project_info = {
                    'Name': project['Name'],
                    'ID': project['_ref'].split('/')[-1].replace('.js', ''),
                    'URL': project['_ref']
                }
                projects_list.append(project_info)

        return projects_list
    else:
        print(response)


def format_creation_date(date_to_be_format):
    if not date_to_be_format:
        return " "
    creation_date = datetime.strptime(date_to_be_format, "%Y-%m-%dT%H:%M:%S.%fZ")

    return creation_date.strftime("%d/%m/%Y")


def format_creation_date_us_format(date_to_be_format):
    if not date_to_be_format:
        return " "
    creation_date = datetime.strptime(date_to_be_format, "%Y-%m-%dT%H:%M:%S.%fZ")

    return br_timezone(creation_date)
    # return creation_date.strftime("%m/%d/%Y %H:%M:%S")


def format_sla_as_time_string(date_to_be_format, sla):
    if not date_to_be_format:
        return ""

    sla_date = datetime.strptime(date_to_be_format, "%Y-%m-%dT%H:%M:%S.%fZ")
    sla_date += timedelta(hours=sla)

    return br_timezone(sla_date)
    # return sla_date.strftime("%m/%d/%Y %H:%M:%S")


def br_timezone(date):
    utc_timezone = pytz.utc
    aware_datetime = date.replace(tzinfo=utc_timezone)

    brasilia_timezone = pytz.timezone('America/Sao_Paulo')  # Ou 'Brazil/East'
    brasilia_datetime = aware_datetime.astimezone(brasilia_timezone)

    return brasilia_datetime.strftime("%m/%d/%Y %H:%M:%S")


def add_business_hours(start_date, hours):
    if not start_date:
        return None

    creation_date = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S.%fZ")

    workdays = [0, 1, 2, 3, 4]

    # Convert start_work_time and end_work_time to datetime objects
    start_work = datetime.strptime("08:00", "%H:%M").time()
    end_work = datetime.strptime("12:00", "%H:%M").time()
    start_lunch = datetime.strptime("13:00", "%H:%M").time()
    end_work_afternoon = datetime.strptime("17:00", "%H:%M").time()

    current_time = creation_date
    added_hours = 0

    while added_hours < hours:
        current_time += timedelta(hours=1)

        # Check if the current time is within business hours and not during lunch break
        if current_time.weekday() in workdays and \
                (start_work <= current_time.time() <= end_work or
                 start_lunch <= current_time.time() <= end_work_afternoon):
            added_hours += 1

    # **Explicitly format current_time before returning**
    return current_time.strftime("%m/%d/%Y %H:%M:%S")


def calculate_business_hours(start_date, end_date):
    start_date = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S.%fZ")
    end_date = datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%S.%fZ")

    if start_date > end_date:
        raise ValueError("Start date must be before end date")

    workdays = [0, 1, 2, 3, 4]  # Monday to Friday
    start_work = datetime.strptime("08:00", "%H:%M").time()
    end_work = datetime.strptime("12:00", "%H:%M").time()
    start_lunch = datetime.strptime("13:00", "%H:%M").time()
    end_work_afternoon = datetime.strptime("17:00", "%H:%M").time()

    current_time = start_date
    business_hours = 0

    while current_time <= end_date:
        current_time += timedelta(hours=1)

        # Check if the current time is within business hours and not during lunch break
        if current_time.weekday() in workdays and \
                (start_work <= current_time.time() <= end_work or
                 start_lunch <= current_time.time() <= end_work_afternoon):
            business_hours += 1

    return business_hours
