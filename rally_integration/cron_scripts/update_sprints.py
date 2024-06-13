import requests
from django_cron import CronJobBase, Schedule

from rally_integration.connection.spreadsheet_connection import get_connection, add_data_to_sheet


class SprintUpdateCron(CronJobBase):
    RUN_EVERY_MIN = 1
    ALLOW_PARALLEL_RUNS = True
    schedule = Schedule(run_every_mins=RUN_EVERY_MIN)
    code = "sprints.update"

    def do(self):
        pass


