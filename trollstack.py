import json
import sys

import requests


def engineer_match(name, engineer):
    if name.lower() == engineer['id'].lower():
        return engineer


owner = sys.argv[1]

r = requests.get(
    "https://review.openstack.org/changes/?q=status:open owner:%s"
    % owner)

change_list = json.loads(r.text[5:])
print("%s has %d patches in review" % (owner, len(change_list)))


for change in change_list:
    change_id = change['_number']

    r = requests.get(
        "https://review.openstack.org/changes/%d/detail" % change_id)

    change = json.loads(r.text[5:])

    patcher_name = change['owner']['username']
    family, project = change['project'].split('/', 2)
    if project.endswith('-specs'):
        project = project[:-6]
    if project == "oslo":
        # Too complicated
        continue

    reviewers_names = [
        review['username']
        for review in change['labels']['Code-Review'].get('all', [])
        if review['value'] < 0]

    if not reviewers_names:
        continue

    # TODO caching or better: group by project
    r = requests.get(
        "http://stackalytics.com/api/1.0/stats/engineers_extended"
        "?release=all&metric=all&module=%s"
        % project)
    engineers = r.json()['stats']

    patcher = None
    reviewers = []

    for engineer in engineers:
        if not patcher:
            patcher = engineer_match(patcher_name, engineer)
        for reviewer in reviewers_names:
            m = engineer_match(reviewer, engineer)
            if m:
                reviewers.append(m)

    for reviewer in reviewers:
        score = 0
        for field, weight in [('bugr', 2),
                              ('bugf', 1),
                              ('commit', 3),
                              ('mark', 1),
                              ('core', 3),
                              ('metric', 1),
                              ('review', 1)]:
            pv = patcher.get(field, 0)
            rv = reviewer.get(field, 0)
            if pv > rv:
                score += weight
            elif pv < rv:
                score -= weight

        if score > 0:
            print("%s lost with %d points and should STFU on %d"
                  % (reviewer['name'], score, change_id))
