from concurrent import futures
from cron import init_cron
from slack_app import init_slack

# Start 2 processes to run our cron and slack app in parallel
with futures.ProcessPoolExecutor(2) as exec:
    # cron = exec.submit(init_cron)
    slack = exec.submit(init_slack)