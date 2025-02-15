# informações que precisam vir do rally
# / tags / priority
# user stories e defects

import requests
import pandas as pd

from django_cron import CronJobBase, Schedule

from rally_integration.connection.spreadsheet_connection import get_connection, add_data_to_sheet, clear_spreadsheet
from rally_integration.cron_scripts.rally_functions import headers, get_project, RALLY_STORIES, RALLY_DEFECTS, \
    format_creation_date_us_format, format_sla_as_time_string, add_business_hours, calculate_business_hours

project_wings = ['Wings Transit']


def get_itens(project, issue_type):
    start_index = 1
    page_size = 30

    if issue_type == 'Story':
        data = [['Issue', 'Summary', 'Status', 'Owner', 'Creation Date', 'In-Progress Date', 'Accepted Date',
                 'Tags', 'Iteration', 'Priority', 'Work Days', 'Expected SLA (Time)', 'Expected SLA (Hours)',
                 'Executed SLA']]
    else:
        data = []

    has_more = True
    total_result_count = 0
    item_count = 0

    print("Project: " + project['Name'] + " - " + issue_type)
    percentagem = 0

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

        itens = response.json()['QueryResult']['Results']

        for item in itens:
            item_count += 1
            percentagem = (100 * item_count) / total_result_count
            print(f"Progress: {percentagem:.2f}%")
            if issue_type == 'Story':
                header = 'HierarchicalRequirement'
            elif issue_type == 'Defect':
                header = 'Defect'
            story_detail = get_story_detail(project, item, item_count, header)
            if story_detail is not None:
                data.append(story_detail)

        if item_count >= total_result_count:
            has_more = False
        else:
            start_index += page_size

    return data


def get_story_detail(project, story, line, header):
    response = requests.get(story['_ref'], headers=headers)

    if response.status_code == 200:
        response_json = response.json()[header]
        us_number = response_json['FormattedID']
        summary = response_json['_refObjectName']
        status = response_json['FlowState']['_refObjectName']
        owner = response_json['Owner']['_refObjectName'] if response_json.get('Owner') else ''
        creation_date = format_creation_date_us_format(response_json['CreationDate'])
        in_progress_date = format_creation_date_us_format(response_json['InProgressDate'])
        accepted_date = format_creation_date_us_format(response_json['AcceptedDate'])

        if accepted_date == " ":
            days_open = pd.date_range(start=creation_date, end=pd.Timestamp.now())
        else:
            days_open = pd.date_range(start=creation_date, end=accepted_date)
        work_days = days_open[days_open.dayofweek < 5]
        num_work_days = len(work_days)

        tags_list = []
        if 'Tags' in response_json and '_tagsNameArray' in response_json['Tags']:
            tags_list = [tag['Name'] for tag in response_json['Tags']['_tagsNameArray']]
        tags = " ".join(tags_list)

        iteration = response_json['Iteration']['_refObjectName'] if response_json.get('Iteration') else ''
        if header == 'Defect':
            priority = response_json['Priority']

            if priority == "Resolve Immediately":
                sla = format_sla_as_time_string(response_json['CreationDate'], 2)
                expected_sla = 2
            elif priority == "High Attention":
                sla = add_business_hours(response_json['CreationDate'], 6)
                expected_sla = 6
            else:
                sla = add_business_hours(response_json['CreationDate'], 24)
                expected_sla = 24
        else:
            priority = response_json['c_Priority']
            expected_sla = ""
            sla = ""

        if response_json['AcceptedDate'] is not None:
            executed_sla = calculate_business_hours(response_json['CreationDate'], response_json['AcceptedDate'])
        else:
            executed_sla = ""

        return [us_number, summary, status, owner, creation_date, in_progress_date, accepted_date, tags,
                iteration, priority, num_work_days, sla, expected_sla, executed_sla]


class RallyConsumerTransitCron(CronJobBase):
    RUN_EVERY_MIN = 1
    ALLOW_PARALLEL_RUNS = True
    schedule = Schedule(run_every_mins=RUN_EVERY_MIN)
    code = "rally.integration"

    # def do(self):
    projects = get_project()
    for project in projects:
        if project['Name'] in project_wings:
            data = get_itens(project, 'Story')
            data.extend(get_itens(project, 'Defect'))

            spreadsheet = get_connection()
            worksheet = spreadsheet.worksheet(project['Name'])
            clear_spreadsheet(worksheet)
            add_data_to_sheet(worksheet, data)

