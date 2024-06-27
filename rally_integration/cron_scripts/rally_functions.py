import requests
from datetime import datetime

RALLY_URL = 'https://rally1.rallydev.com/slm/webservice/1.29/subscription.js?fetch=Workspaces,Projects,Name&pretty=true'

RALLY_STORIES = 'https://rally1.rallydev.com/slm/webservice/v2.0/hierarchicalrequirement?query=' \
                '(Project.ObjectID = :project_id)&start=:start_index&pagesize=:page_size'

RALLY_DEFECTS = 'https://rally1.rallydev.com/slm/webservice/v2.0/defects?query=' \
                '(Project.ObjectID = :project_id)&start=:start_index&pagesize=:page_size'


headers = {
    # 'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json',
    'zsessionid': '_AMFr0GPRQrKZMoDMDTP1C9fpxyxU3Xs8pbUcYC1RY'
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
    return creation_date.strftime("%m/%d/%Y")
