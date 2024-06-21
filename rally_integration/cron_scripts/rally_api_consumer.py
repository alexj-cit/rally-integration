import requests
from django_cron import CronJobBase, Schedule
from datetime import datetime

from rally_integration.connection.spreadsheet_connection import get_connection, add_data_to_sheet, clear_spreadsheet
from rally_integration.cron_scripts.rally_functions import headers, get_project, RALLY_STORIES, format_creation_date

# Settings
project_wings = ['Wings Ranger', 'Wings Mustang']

sprint_spreadsheet = None


def get_stories(project):
    start_index = 1
    page_size = 30

    data = [['Issue', 'Summary', 'Status', 'Points', 'Development Start', 'Development Finish', 'Business Accept',
             'Activate', 'Tasks', 'Development Bugs', 'Business Bugs', 'Estimated', 'To Do']]

    has_more = True
    total_result_count = 0
    story_count = 0

    print("Project: " + project['Name'])
    evolution = 0

    while has_more:
        url = RALLY_STORIES.replace(':project_id', project['ID']).replace(':start_index',
                                                                          str(start_index)).replace(':page_size',
                                                                                                    str(page_size))

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f'Erro: {response.status_code}')
            return None

        if total_result_count == 0:
            total_result_count = response.json()['QueryResult']['TotalResultCount']

        stories = response.json()['QueryResult']['Results']

        for story in stories:
            story_count += 1
            evolution = (100 * story_count) / total_result_count
            print(f"Progress: {evolution:.2f}%")
            data.append(get_story_detail(project, story, story_count))

        if story_count >= total_result_count:
            has_more = False
        else:
            start_index += page_size

    spreadsheet = get_connection()
    worksheet = spreadsheet.worksheet(project['Name'])
    clear_spreadsheet(worksheet)
    add_data_to_sheet(worksheet, data)


def get_sprint(date_str):
    global sprint_spreadsheet

    if not date_str or date_str.strip() == '':
        return date_str

    if sprint_spreadsheet is None:
        spreadsheet = get_connection()
        sprint_spreadsheet = spreadsheet.worksheet('Sprints - Config')

    rows = sprint_spreadsheet.get_all_values()

    date = datetime.strptime(date_str, "%d/%m/%Y")

    for row in rows[1:]:
        sprint_name = row[0]
        start_date_str = row[1]
        end_date_str = row[2]

        start_date = datetime.strptime(start_date_str, "%d/%b/%y")
        end_date = datetime.strptime(end_date_str, "%d/%b/%y")

        if start_date <= date <= end_date:
            return sprint_name


def get_story_detail(project, story, line):
    response = requests.get(story['_ref'], headers=headers)

    if response.status_code == 200:
        response_json = response.json()['HierarchicalRequirement']
        us_number = response_json['FormattedID']
        summary = response_json['_refObjectName']
        todo = response_json['TaskRemainingTotal']
        status = response_json['FlowState']['_refObjectName']
        tasks_count = response_json['Tasks']['Count']
        points = response_json['PlanEstimate']

        estimate = response_json['TaskEstimateTotal']
        if not estimate:
            estimate = 0.0

        defects_count = response_json['Defects']['Count']
        business_count = 0
        dev_count = 0
        if defects_count > 0:
            business_count = 0
            dev_count = 0

            defect = response_json['Defects']
            defect_response = requests.get(defect['_ref'], headers=headers)
            if defect_response.status_code == 200:
                defect_return = defect_response.json()['QueryResult']['Results']
                for result in defect_return:
                    if result['Environment'] == 'Test':
                        business_count += 1
                    else:
                        dev_count += 1

        sheet = f"'{project['Name']} - Sprints'"
        dev_start = f'=IFERROR(VLOOKUP(A{line + 1},{sheet}!A2:D,4,FALSE),"")'
        dev_finish = f'=IFERROR(VLOOKUP(A{line + 1},{sheet}!A2:E,5,FALSE),"")'

        accepted_date = response_json['AcceptedDate']
        buss_accept = get_sprint(format_creation_date(accepted_date))

        return [us_number, summary, status, points, dev_start, dev_finish, buss_accept, '',
                tasks_count, dev_count, business_count, estimate,
                todo]


class RallyConsumerCron(CronJobBase):
    RUN_EVERY_MIN = 1
    ALLOW_PARALLEL_RUNS = True
    schedule = Schedule(run_every_mins=RUN_EVERY_MIN)
    code = "rally.integration"

    # def do(self):
    projects = get_project()
    for project in projects:
        if project['Name'] in project_wings:
            get_stories(project)
