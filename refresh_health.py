"""Select unreported failures from the newest run of each workflow."""


def latest_failures(runs, notified):
    latest = {}
    for run in runs:
        workflow = run['workflowName']
        order = (run['createdAt'], int(run['databaseId']), int(run['attempt']))
        if workflow not in latest or order > latest[workflow][0]:
            latest[workflow] = (order, run)
    for _, run in latest.values():
        identity = f"{run['databaseId']}:{run['attempt']}"
        if (run['status'] == 'completed'
                and run['conclusion'] in ('failure', 'timed_out', 'action_required')
                and identity not in notified):
            yield run
