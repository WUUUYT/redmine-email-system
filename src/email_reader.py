import re
import logging
import requests
import base64
from datetime import datetime, timezone, timedelta
from pathlib import Path
from bs4 import BeautifulSoup
from config.settings import *



class EmailReader:
    def __init__(self, 
                 project_id = None,
                 access_token = None,
                 mailbox=EMAIL_CONFIG['mailbox'],
                 time_file=EMAIL_CONFIG['processed_files']):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        self.mailbox = mailbox
        self.time_file = Path(__file__).resolve().parent / time_file
        self.project_id = project_id
        self.emails = []
        self.emails_data = []
        self.logger = logging.getLogger(__name__)

    def connect_read(self):
        self.logger.info(f"{'='*5} Email check cycle began {'='*5}")
        last_time = self.load_processed_time()
        
        url = f"https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$orderby=receivedDateTime asc&$filter=receivedDateTime gt {last_time}&$top=10"
        while url:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                print("FAIL", response.status_code, response.text)
                break
            data = response.json()
            emails = data.get("value", [])
            self.emails.extend(emails)
            url = data.get("@odata.nextLink")
        self.logger.info(f"{len(self.emails)} email IDs loaded.")

    def load_processed_time(self):
        if not os.path.exists(self.time_file):
            self.logger.info(f"No email time file found. Returning the current time.")
            return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        try:
            with open(self.time_file, 'r') as f:
                time_str = f.read().strip()
                if time_str:
                    self.logger.info(f"Last processed time loaded: {time_str}")
                    dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    dt_plus_one = dt + timedelta(seconds=1)
                    return dt_plus_one.isoformat(timespec='seconds').replace('+00:00', 'Z')
                else:
                    self.logger.info("Time file is empty. Returning current time.")
                    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        except IOError as e:
            self.logger.info(f"Error loading time from file. Returning current time.")
            return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        
    def reading_emails(self):
        if not self.emails:
            self.logger.info('No new emails.')
        else:
            for email in self.emails:
                # Subject
                issue_id, subject = self.clean_subject(email["subject"])

                emailignore = APP_CONFIG["projects"][self.project_id]["emailignore"]
                if emailignore["startwith"]:   
                    escaped = [re.escape(p) for p in emailignore["startwith"]]
                    pattern = r'^(?:' + '|'.join(escaped) + ')'
                    regex = re.compile(pattern)
                    if bool(regex.match(subject)):
                        continue
                if emailignore["contain"]:
                    escaped = [re.escape(p) for p in emailignore["contain"]]
                    pattern = r'(?:' + '|'.join(escaped) + r')'
                    if re.search(pattern, subject):
                        continue
                if emailignore["endwith"]:
                    escaped = [re.escape(p) for p in emailignore["endwith"]]
                    pattern = r'(?:' + '|'.join(escaped) + r')$'
                    if re.search(pattern, subject):
                        continue

                # Name and Address
                from_info = email.get("from", {}).get("emailAddress", {})
                name = from_info.get("name", "Unknown")
                address = from_info.get("address", "Unknown")
                # Time
                email_date = datetime.strptime(email['receivedDateTime'], "%Y-%m-%dT%H:%M:%SZ").astimezone()
                # Body
                html_content = email["body"]["content"]
                plain_text = BeautifulSoup(html_content, "html.parser").get_text()
                plain_text = self.clean_email_body(plain_text)
                # Attachments
                message_id = email["id"]
                attachments_dir = Path(__file__).resolve().parent / "attachments" / {message_id}
                os.makedirs(attachments_dir, exist_ok=True)
                file_paths = []
                attachment_url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/attachments"
                att_response = requests.get(attachment_url, headers=self.headers)
                if att_response.status_code != 200:
                    print(f"FAIL: {att_response.status_code} {att_response.text}")
                    continue
                attachments = att_response.json().get("value", [])
                for att in attachments:
                    filename = att["name"]
                    # content_type = att["contentType"]
                    # size = att["size"]
                    # content_id = att.get("contentId")
                    # Download att
                    if att["@odata.type"] == "#microsoft.graph.fileAttachment":
                        content_bytes = att["contentBytes"]
                        content_bytes = base64.b64decode(content_bytes)
                        filepath = os.path.join(attachments_dir, filename)
                        with open(filepath, "wb") as f:
                            f.write(content_bytes)
                        file_paths.append(filepath)

                email_data = {
                'subject': subject.strip(),
                'issue_id': issue_id, # can delete
                'sender': name,
                'email_addr': address,
                'time': email_date,
                'body': plain_text.strip(),
                'attachments': file_paths}
                self.emails_data.append(email_data)
            # Save the latest time
            latest_time = self.emails[-1]["receivedDateTime"]
            with open(self.time_file, "w") as f:
                f.write(latest_time)
        self.logger.info(f"{'='*5} Email check cycle finished {'='*5}")

    # def clean_subject(self, subject):
    #    return re.sub(r'^(?:RE:\s*|FW:\s*|FWD:\s*|回复:\s*|转发:\s*|回覆:\s*|轉寄:\s*|轉發:\s*)+', '', subject, flags=re.IGNORECASE).strip()
    def clean_subject(self, subject):
        cleaned_subject = re.sub(
            r'^(?:RE:\s*|FW:\s*|FWD:\s*|回复:\s*|转发:\s*|回覆:\s*|轉寄:\s*|轉發:\s*)+', '', subject, flags=re.IGNORECASE).strip()
        match = re.search(r'#(\d+)', cleaned_subject)
        issue_id = int(match.group(1)) if match else None

        if ']' in cleaned_subject:
                subject_only = cleaned_subject.split(']', 1)[1].strip()
        else:
            subject_only = cleaned_subject
        return issue_id, subject_only
    
    # def clean_email_body(self, body):
    #    warning_pattern = r"(?i)Caution:\s*This is an external email\. Please take care when clicking links or opening attachments\. When in doubt, contact your IT Department"
    #    return re.sub(warning_pattern, "", body, flags=re.DOTALL).strip()
    def clean_email_body(self, body):
        warning_pattern = r"(?i)Caution:\s*This is an external email\. Please take care when clicking links or opening attachments\. When in doubt, contact your IT Department"
        body = re.sub(warning_pattern, "", body, flags=re.DOTALL).strip()
        reply_split_pattern = r"----------Reply above this line to add a note----------"
        body = re.split(reply_split_pattern, body, flags=re.IGNORECASE)[0].strip()
        meta_block_pattern = r"(?ims)^From:.*?\nSent:.*?\nTo:.*?\nSubject:.*?$"
        meta_block_pattern = r"(?i)From:.*?Sent:.*?To:.*?Subject:.*"
        body = re.sub(meta_block_pattern, "", body).strip()
        return body

if __name__ == '__main__':   

    None





    # access_token = ''
    # emailreader = EmailReader(access_token=access_token)
    # emailreader.connect_read()
    # emailreader.reading_emails()
    # print([data['subject'] for data in emailreader.emails])
    #emailreader.reading_emails()
    #print(emailreader.emails_data[0])
    # body = 'Hi, There are some supplementary documents. Please see attached for your information.Best,User From: Yitong Wu <Yitong.Wu@FII-NA.com> Sent: Monday, June 30, 2025 10:37 AMTo: userwithrequests@outlook.comSubject: Re: [Issue #2604] Add A function in B environment (demo)'
    # print(emailreader.clean_email_body(body))
    # emailreader.connect()
    # emailreader.find_new()
    # emailreader.read_all()
    # emailreader.save_processed_uid()
    # 