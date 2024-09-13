import requests
from django_cron import CronJobBase, Schedule
from datetime import datetime

from rally_integration.connection.spreadsheet_connection import get_connection, add_data_to_sheet, clear_spreadsheet
from rally_integration.cron_scripts.rally_functions import headers, get_project, RALLY_STORIES, format_creation_date, \
    RALLY_DEFECTS

# Settings
project_wings = ['Wings Ranger', 'Wings Mustang']

sprint_spreadsheet = None
rows_sprints = None


def get_stories(project, issue_type):
    start_index = 1
    page_size = 30

    if issue_type == 'Story':
        data = [['Issue', 'Summary', 'Status', 'Points', 'Development Start', 'Development Finish', 'Business Accept',
                'Activate', 'Tasks', 'Development Bugs', 'Business Bugs', 'Estimated', 'To Do']]
    elif issue_type == 'Defect':
        data = [['Issue', 'Summary', 'Status', 'Parent', 'Tags', 'Development Start', 'Development Finish', 'Business Accept',
                 'Activate']]

    has_more = True
    total_result_count = 0
    story_count = 0

    print("Project: " + project['Name'] + ' - ' + issue_type)
    evolution = 0

    while has_more:
        if issue_type == 'Story':
            url = RALLY_STORIES.replace(':project_id', project['ID']).replace(':start_index',
                                                                              str(start_index)).replace(':page_size',
                                                                                                        str(page_size))
        elif issue_type == 'Defect':
            url = RALLY_DEFECTS.replace(':project_id', project['ID']).replace(':start_index',
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
            if issue_type == 'Story':
                header = 'HierarchicalRequirement'
            elif issue_type == 'Defect':
                header = 'Defect'
            data.append(get_story_detail(project, story, story_count, header))

        if story_count >= total_result_count:
            has_more = False
        else:
            start_index += page_size

    return data


def save_data(sheet_name, data):
    spreadsheet = get_connection()
    worksheet = spreadsheet.worksheet(sheet_name)
    clear_spreadsheet(worksheet)
    add_data_to_sheet(worksheet, data)


def get_sprint(date_str):
    global sprint_spreadsheet
    global rows_sprints

    if not date_str or date_str.strip() == '':
        return date_str

    if sprint_spreadsheet is None:
        spreadsheet = get_connection()
        sprint_spreadsheet = spreadsheet.worksheet('Sprints - Config')
        rows_sprints = sprint_spreadsheet.get_all_values()

    date = datetime.strptime(date_str, "%d/%m/%Y")

    for row in rows_sprints[1:]:
        sprint_name = row[0]
        start_date_str = row[1]
        end_date_str = row[2]

        start_date = datetime.strptime(start_date_str, "%d/%b/%y")
        end_date = datetime.strptime(end_date_str, "%d/%b/%y")

        if start_date.date() <= date.date() <= end_date.date():
            return sprint_name

    return date_str


def get_story_detail(project, story, line, header):
    response = requests.get(story['_ref'], headers=headers)

    if response.status_code == 200:
        response_json = response.json()[header]
        us_number = response_json['FormattedID']
        summary = response_json['_refObjectName']
        status = response_json['FlowState']['_refObjectName']
        if header == "HierarchicalRequirement":
            todo = response_json['TaskRemainingTotal']
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
        elif header == "Defect":
            parent = ""
            requirement = response_json.get('Requirement')
            if requirement and '_refObjectName' in requirement:
                parent = requirement['_refObjectName']
                parent = f'''=IFERROR(FILTER('{project["Name"]}'!A:A, '{project["Name"]}'!B:B = "{parent.replace('"', '""')}"),"")'''

            tags_list = []
            if 'Tags' in response_json and '_tagsNameArray' in response_json['Tags']:
                tags_list = [tag['Name'] for tag in response_json['Tags']['_tagsNameArray']]
            tags = " ".join(tags_list)

        sheet = f"'{project['Name']} - Sprints'"
        dev_finish = f'=IFERROR(VLOOKUP(A{line + 1},{sheet}!A2:B,2,FALSE),"")'
        activated = f'=IFERROR(VLOOKUP(A{line + 1},{sheet}!A2:C,3,FALSE),"")'

        in_progress_date = response_json['InProgressDate']
        dev_start = ''
        if in_progress_date is not None:
            dev_start = get_sprint(format_creation_date(in_progress_date))

        accepted_date = response_json['AcceptedDate']
        buss_accept = ''
        if accepted_date is not None:
            buss_accept = get_sprint(format_creation_date(accepted_date))

        if header == 'HierarchicalRequirement':
            return [us_number, summary, status, points, dev_start, dev_finish, buss_accept, activated,
                    tasks_count, dev_count, business_count, estimate,
                    todo]
        elif header == 'Defect':
            return [us_number, summary, status, parent, tags, dev_start, dev_finish, buss_accept, activated]


class RallyConsumerCron(CronJobBase):
    RUN_EVERY_MIN = 1
    ALLOW_PARALLEL_RUNS = True
    schedule = Schedule(run_every_mins=RUN_EVERY_MIN)
    code = "rally.integration"

    # def do(self):
    projects = get_project()
    for project in projects:
        if project['Name'] in project_wings:
            data = get_stories(project, 'Story')
            save_data(project['Name'], data)

            data = get_stories(project, 'Defect')
            save_data(project['Name'] + ' - Defects', data)
