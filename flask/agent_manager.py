import crontab
import datetime
import glob
import pytoml
import logging
import config
import os

LOG = logging.getLogger('alerts')
def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance
@singleton
class AgentChooser:
    def __init__(self):
        self.url = config.REPO_URL
        self.path = config.REPO_PATH
        self.parent_path = "/".join(self.path.split("/")[:-1])
        self.operations_path = os.path.join(self.path, "teams/operations")
        self.agents = []


    def pull_repo(self):
        LOG.debug("Pulling the repo")
        if os.path.exists(self.path):
            os.system('cd {} && git pull'.format(self.path))
        else:
            os.system('mkdir -p {}'.format(self.parent_path))
            os.system('cd {} && git clone {}'.format(self.parent_path, self.url))

    def get_file_paths(self):
        LOG.debug("Get paths for agents person.toml file")
        file_paths = []
        for file_path in glob.iglob('{}/**/*.toml'.format(self.operations_path), recursive=True):
            file_paths.append(file_path)
        return file_paths


    def get_current_agent(self):
        for agent in self.agents:
            if agent.is_working:
                return agent
        raise Exception("No agent is working now")

    def update_agents(self):
        """
        this method used to update agents list with the new data
        """
        LOG.debug('updating agents')
        agents = []
        for path in self.get_file_paths():
            try:
                with open(path, 'rb') as f:
                    toml = pytoml.load(f)
                    escalation = toml['escalation'][0]
                    agent = Agent(
                                 name = "{} {}".format(toml['first_name'], toml['last_name']),
                                 telegram = toml['telegram'].strip("@"),
                                 backup = escalation['backup'],
                                 backup_time = escalation['backup_time'],
                                 escalation_path = escalation['escalation_path'],
                                 working_period = escalation['period'],
                                 exclude_period = escalation['exclude'],
                                 reports_into = toml['reports_into'],
                                 )

                    agents.append(agent)
            except:
                LOG.error("Can not load toml file at {}".format(path))
        self.agents = agents

class Agent():
    def __init__(self, name=None, telegram=None, backup=None, backup_time=None, escalation_path=None, working_period=None, exclude_period=None, reports_into=None):
        self.name = name
        self.telegram = telegram
        self.backup = backup
        self.backup_time = backup_time
        self.escalation_path = escalation_path
        self.working_period = working_period
        self.exclude_period = exclude_period
        self.reports_into = reports_into

    def is_working(self):
        """
        check if an agent is working now or not base on working and exclude period times
        """
        if is_matching(self.exclude_period):
            return False
        if is_matching(self.working_period):
            return True
        return False

    def is_matching(self, period):
        now = datetime.datetime.now()
        for item in period:
            cron = crontab.CronTab(item.split(":")[0])
            matched = True
            if cron.matchers.month.allowed and now.month not in cron.matchers.month.allowed:
                matched = False
            if cron.matchers.day.allowed and now.day not in cron.matchers.day.allowed:
                matched = False
            if cron.matchers.hour.allowed and now.hour not in cron.matchers.hour.allowed:
                matched = False
            if cron.matchers.weekday.allowed and now.weekday not in cron.matchers.weekday.allowed:
                matched = False
            if matched:
                return True
        else:
            return False
