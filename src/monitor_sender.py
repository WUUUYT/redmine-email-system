import smtplib
import logging
import requests
import json
from pathlib import Path
from html2text import html2text
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from redminelib import Redmine
from config.settings import *
from config.redmine_info import *


class MonitorSender():
    def __init__(self,
                 project_id = None,
                 redmine_url = REDMINE_CONFIG['url'], # Default
                 redmine_apikey = REDMINE_CONFIG['apikey'], # Default
                 issue_file = REDMINE_CONFIG['processed_files'], # Default
                 access_token = None,
                 send_url = "https://graph.microsoft.com/v1.0/me/sendMail", # Default
                 ):
        self.project_id = project_id
        self.redmine = Redmine(redmine_url,
                               key = redmine_apikey,
                               raise_attr_exception=False)
        self.updated_issues = None
        self.issue_file = Path(__file__).resolve().parent / issue_file
        self.access_token = access_token
        self.url = send_url
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        # logging
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"{'='*5} Monitor cycle began {'='*5}")

    def send_email(self, recipient, subject, html_body=None):
        email_msg = {
            "message": {
                "subject": 'Re: ' + subject,
                "body": {
                    "contentType": "HTML",
                    "content": html_body
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": recipient
                        }
                    }
                ]
            }
        }
        requests.post(self.url, headers=self.headers, data=json.dumps(email_msg))
        self.logger.info(f"-----Email has been sent to '{recipient}' with subject '{subject}'")

    def find_updated_issue_within(self, time_interval_minutes = APP_CONFIG['check_interval']):
        last_time = None
        if os.path.exists(self.issue_file):
            with open(self.issue_file, 'r') as f:
                last_time = f.read().strip()
                if last_time:
                    timestamp = (datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S"))\
                            .replace(tzinfo=timezone.utc)\
                            .strftime("%Y-%m-%dT%H:%M:%SZ")
        time_ago = datetime.now(timezone.utc) - timedelta(minutes=time_interval_minutes)
        if not last_time:
            timestamp = time_ago.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.logger.info('Timestamp determined.')
        # Starting filtering
        recent_updated = self.redmine.issue.filter(
            project_id = self.project_id,
            updated_on = f">={timestamp}",
            status_id  = '*',
            include    = 'assigned_to')
        timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        recent_updated = [issue for issue in recent_updated if issue.updated_on > timestamp]

        self.updated_issues = []
        for issue in recent_updated:
            created_on = issue.created_on
            if created_on.tzinfo is None:
                created_on = created_on.replace(tzinfo=timezone.utc)
            if created_on < time_ago:
                self.updated_issues.append(issue)

        if not self.updated_issues:
            self.logger.info('No updated issues found.')
        else:
            self.logger.info('updated emails found')
            latest_updated_time = max(issue.updated_on for issue in self.updated_issues)
            with open(self.issue_file, 'w') as f:
                    f.write(str(latest_updated_time))
            self.logger.info('Last updated time {latest_updated_time} saved')

    def resolve_value(self, field_name, value):
        if value is None:
            return "None"
        try:
            value = int(value)
        except:
            return value
        if field_name == 'status_id':
            return status_map.get(value, f"[Unknown status {value}]")
        elif field_name == 'priority_id':
            return priority_map.get(value, f"[Unknown priority {value}]")
        elif field_name == 'assigned_to_id':
            return user_map.get(value, f"[Unknown priority {value}]")
        else:
            return value

    def process_emails(self):
        for issue in self.updated_issues:
            journal = list(issue.journals)[-1] if issue.journals else None

            if not journal or journal.created_on != issue.updated_on:
                continue
            if not journal.detials and journal.notes.startswith("Note author ("):
                continue
            names = [detail['name'] for detail in journal.details]
            flag = any([
                APP_CONFIG['reminderconfig']['status_change'] and 'status_id' in names,
                APP_CONFIG['reminderconfig']['priority_change'] and 'priority_id' in names,
                APP_CONFIG['reminderconfig']['assignee_change'] and 'assigned_to_id' in names,
                APP_CONFIG['reminderconfig']['tracker_change'] and 'tracker_id' in names,
                APP_CONFIG['reminderconfig']['notes_change'] and bool(journal.notes)
            ])
            if not flag: continue
            # recipient
            recipient = issue.custom_fields[1]['value']
            if '@' not in recipient:
                self.logger.info(f'Issue (ID: {issue.id}): No email address found ')
                continue
            self.logger.info(f'Issue (ID: {issue.id}): email to be sent ...')
            # Assignee
            if issue.assigned_to:
                body_assignee = issue.assigned_to.name
            else:
                body_assignee = 'None'
            # List of spent hours
            # time_entries = self.redmine.time_entry.filter(issue_id=issue.id)
            # if time_entries:
            #     body_spent_hours = ''
            #     for entry in time_entries:
            #         body_spent_hours += f' {entry.user.name} spent {entry.hours} hours' + '\n'
            #     body_spent_hours = body_spent_hours.rstrip('\n')
            # else:
            #     body_spent_hours = 'None'
            # Notes
            journals = self.redmine.issue.get(issue.id, include='journals').journals
            notes = [j for j in journals if getattr(j, 'notes', None)]
            if not notes:
                new_note = 'No note found.'
            else:
                last_note = notes[-1]
                new_note = last_note.notes
                # url
            issue_url = f'{REDMINE_CONFIG["url"]}issues/{issue.id}'
            # Latest change
            # journal = list(issue.journals)[-1] if issue.journals else None
            # html_changes = "<ul>"
            # if journal and journal.created_on == issue.updated_on:
            #     if journal.details:
            #         for detail in journal.details:
            #             name = detail['name']
            #             if name == '1':
            #                 name = 'Business Unit'
            #             elif name == '3':
            #                 name = 'Deliverables'
            #             elif name == '4':
            #                 name = 'Location'
            #             elif name == '5':
            #                 name = 'Requestor'
            #             old = detail.get('old_value', 'None')
            #             new = detail.get('new_value', 'None')
            #             old = self.resolve_value(name, old)
            #             new = self.resolve_value(name, new)
            #             html_changes += f"<li><strong>{name}</strong> changed from <span style='color:red;'>{old}</span> to <span style='color:green;'>{new}</span></li>"
            #     if journal.notes:
            #         html_changes += f"<li><strong>Note: </strong>{journal.notes}</li>"
            #     html_changes_total = f"<p>Updated by: {journal.user}</p><p>{html_changes.replace('\n', '<br>')}</p>"
            # else:
            #     html_changes_total = "<p>None</p>"

            html_total_body = f'''
            <html>
            <head></head>
            <body>
                <P>{'-'*10 + 'Reply above this line to add a note' + '-'*10}<P>
                <P>
                <p>Hi {recipient}, </p>
                <p>The issue (ID: {issue.id}) you submitted on {issue.created_on}
                with subject '{issue.subject}' has been updated.
                Meanwhile, you can reply to this email if you have any additional questions or details.<p></p>
                Please click this </strong> <a href="{issue_url}">link</a> for details. Or you can check some of the related attributes of this issue as shown below. </p>
                <p>Sincerely,<br>
                IT Team</p>
                <i><strong>NOTE</strong>: If you reply via email, try not to modify the subject, as it is the key to matching the correct issue. Otherwise, please include your issue id in the subject in the format (e.g., #1234), or simply use your issue subject as the email subject.</i>
                <hr style="height:1px; border:none; background: linear-gradient(to right, #ccc, #333, #ccc); margin: 10px 0;">
                <p><strong style="font-size:20px;">Issue Attributes</strong></p>
                <table style="font-size:14px; line-height:1.6;">
                    <tr><td><strong>Updated Time:</strong></td>
                    <td>{issue.updated_on}</td></tr>
                    <tr><td><strong>Status:</strong></td>
                    <td>{issue.status}</td></tr>
                    <tr><td><strong>Priority:</strong></td>
                    <td>{issue.priority}</td></tr>
                    <tr><td><strong>Tracker:</strong></td>
                    <td>{issue.tracker}</td></tr>
                    <tr><td><strong>Assignee:</strong></td>
                    <td>{body_assignee}</td></tr>
                    <tr><td><strong>New Note:</strong></td>
                    <td>{new_note.replace('\n', '<br>')}</td></tr>
                    </table>
            </body>
            </html>
            '''
            # Codes for Spent Hours
            # <tr><td><strong>Spent Hours:</strong></td>
            #    <td>{body_spent_hours.replace('\n', '<br>') if body_spent_hours != 'None' else 'None'}</td></tr>
            # Codes for the latest change (Can be inserted into html total body)
            # <hr style="height:1px; border:none; background: linear-gradient(to right, #ccc, #333, #ccc); margin: 10px 0;">
            #    <div style="font-size: 20px; margin: 10px 0;"><strong>Latest Change</strong></div>
            #    <div>{html_changes_total}</div>
            #    <hr style="height:1px; border:none; background: linear-gradient(to right, #ccc, #333, #ccc); margin: 10px 0;">

            self.send_email(recipient,
                            f'[Issue #{issue.id}] ' + issue.subject,
                            html_total_body)
        self.logger.info(f"{'='*5} Monitor cycle finished {'='*5}")

    def main(self):
        self.find_updated_issue_within()
        self.process_emails()

if __name__ == '__main__':
    #logging.config.dictConfig(LOGGING_CONFIG)
    access_token = ''
    monitorsender = MonitorSender(access_token=access_token)
    monitorsender.main()
    #print(user_map[54])
    # print([issue.id for issue in redminemonitor.updated_issues])
    # issue = redminemonitor.redmine.issue.get(2308)
    # time_entries = redminemonitor.redmine.time_entry.filter(issue_id=2308)
    # body_spent_hours = 'Spent hours: \n'
    # if time_entries:
    #     for entry in time_entries:
    #         body_spent_hours += f"    {entry.user.name} spent {entry.hours} hours" + '\n'
    # print(body_spent_hours)
