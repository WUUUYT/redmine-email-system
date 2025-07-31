import logging
from html2text import html2text
from email.mime.text import MIMEText
import datetime
import base64
import requests
import json
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from config.settings import *
from datetime import date
from redminelib import Redmine

class RedmineHandler():
    def __init__(self,
                 project_id = '',
                 redmine_url = REDMINE_CONFIG['url'],
                 redmine_apikey = REDMINE_CONFIG['apikey'],
                 send_url = "https://graph.microsoft.com/v1.0/me/sendMail",
                 access_token = None,
                 emails_data = None):
        # One per login
        self.redm_url = redmine_url
        self.redm_apikey = redmine_apikey
        self.project_id = project_id
        self.emails_data = emails_data
        self.redmine = None
        # One per email
        self.issue = None
        self.subject = None
        self.sender = None
        self.email_addr = None
        self.body = None
        self.time = None
        self.attachments = []
        # Graph mail.send
        self.url = send_url
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        # Logging
        self.logger = logging.getLogger(__name__)

    def login(self):
        self.logger.info(f"{'='*5} Redmine handling cycle began {'='*5}")
        try:
            self.redmine = Redmine(self.redm_url, key=self.redm_apikey)
            self.redmine.user.get('current')
            self.logger.info('Connected to Redmine.')
        except Exception as e:
            self.logger.error(f'Failed to connect to Redmine: {e}')
            self.redmine = None
        #self.redmine = Redmine(self.redm_url, username = self.redm_user, password = self.redm_pass)
        #self.logger.info('Connected to Redmine.')

    def load_email(self, index):
        email_data = self.emails_data[index]
        self.subject = email_data['subject']
        self.issue_id = email_data['issue_id'] # can delete
        self.sender = email_data['sender']
        self.email_addr = email_data['email_addr']
        self.time = email_data['time']
        self.body = email_data['body']
        if email_data['attachments']:
            self.attachments = email_data['attachments']
        else:
            self.attachments = []
        self.logger.info('One email loaded.')

    def find_issue_id_by_subject(self):
        all_matches = self.redmine.issue.filter(
                                        project_id = self.project_id,
                                        subject=self.subject, 
                                        status_id='*', 
                                        limit=100)
        self.issue = None
        for issue in all_matches:
            if issue.subject.strip() == self.subject:
                self.issue = issue
                self.logger.info(f'-----Issue {issue.id} matched.')

    def update_issue(self):
        # Writing update content to notes
        header = f"Note author ({self.sender}):"
        separator = "-" * 30
        self.issue.notes = f"{header}\n{separator}\n{self.body}"
        uploads = []
        for file_path in self.attachments:
            path_obj = Path(file_path)
            if path_obj.exists():
                uploaded_file = self.redmine.upload(file_path)
                uploads.append({
                    'path': file_path,
                    'token': uploaded_file['token'],})
        self.issue.uploads = uploads
        # Save changes to this issue
        self.issue.save()
        self.logger.info(f'-----Issue updated success with ID: {self.issue.id}.')

    def send_email(self, html_body=None):
        # attachments = []
        # for file_path in self.attachments:
        #     filename = os.path.basename(file_path)
        #     if filename.endswith(".pdf"):
        #         content_type = "application/pdf"
        #     elif filename.endswith(".png"):
        #         content_type = "image/png"
        #     elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
        #         content_type = "image/jpeg"
        #     elif filename.endswith(".txt"):
        #         content_type = "text/plain"
        #     else:
        #         content_type = "application/octet-stream"
        #     with open(file_path, "rb") as f:
        #         content_bytes = base64.b64encode(f.read()).decode()

        #     attachment = {
        #         "@odata.type": "#microsoft.graph.fileAttachment",
        #         "name": filename,
        #         "contentBytes": content_bytes,
        #         "contentType": content_type
        #     }
        #     attachments.append(attachment)
            
        email_msg = {
            "message": {
                "subject": f'[Issue #{self.issue.id}] ' + self.subject,
                "body": {
                    "contentType": "HTML",
                    "content": html_body
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": self.email_addr
                        }
                    }
                ]
            }
        }
        response = requests.post(self.url, headers=self.headers, data=json.dumps(email_msg))
        if response.status_code >= 200 and response.status_code < 300:
            self.logger.info(f"--Email '{self.subject}' is secussfully sent to '{self.email_addr}'.")
        else:
            self.logger.info(f"--Email '{self.subject}' to '{self.email_addr}' Failed to send.")

    def create_issue(
            self,
            start_date = date.today()
            ):
        uploads = []
        for file in self.attachments:
            upload_path = file
            path_obj = Path(upload_path)
            if path_obj.exists():
                uploaded_file = self.redmine.upload(upload_path)
                uploads.append({
                    'path': upload_path,
                    'token': uploaded_file['token'],})
                
        createdefault = APP_CONFIG['projects'][self.project_id]['createdefault']

        self.issue = self.redmine.issue.create(
            project_id     = self.project_id, #under which project to create an issue
            subject        = self.subject, # from email
            description    = self.body, # from email
            status_id      = createdefault['status_id'],
            assigned_to_id = createdefault['assigned_to_id'],
            tracker_id     = createdefault['tracker_id'],
            priority_id    = createdefault['priority_id'],
            custom_fields=[
                {'id': 1, 
                 'value': createdefault['business_unit']},
                {'id': 5, 
                 'value': self.email_addr}],
            start_date = start_date,
            uploads = uploads
            )
        self.logger.info(f'--Issue created success with ID: {self.issue.id}.')

        html_total_body = f'''\
            <html>
            <head></head>
            <body>
                <P>{'-'*10 + 'Reply above this line to add a note' + '-'*10}<P>
                <P>
                <p>Hi {self.sender}, </p>
                <p>The IT team has received your request and created an related issue (ID: {self.issue.id}) on {self.issue.created_on} 
                with subject '{self.issue.subject}'. 
                Meanwhile, you can reply to this email if you have any additional questions or details.<p></p>

                <p>Sincerely,<br>
                IT Team</p>
                <i><strong>NOTE</strong>: If you reply via email, try not to modify the subject, as it is the key to matching the correct issue. Otherwise, please include your issue id in the subject in the format (e.g., #1234), or simply use your issue subject as the email subject.</i>
            </body>
            </html>
            '''
        self.send_email(html_total_body)
        

    def redmine_write(self):
        for i in range(len(self.emails_data)):
            self.load_email(i)
            if self.issue_id:
                try:
                    self.issue = self.redmine.issue.get(self.issue_id)
                except Exception as e:
                    self.issue = None
            else:
                self.find_issue_id_by_subject()
            if self.issue:
                self.update_issue()
            else:
                self.create_issue()
        self.logger.info(f"{'='*5} Redmine handling cycle finished {'='*5}")

if __name__ == '__main__':
    pass 
