# RedmineTicket Automation System

An automated system that converts emails into Redmine issues using Microsoft Graph API, NLP-based task classification, and containerized deployment. This solution replaces a $4K/year third-party service while significantly improving efficiency and routing accuracy.

## 🚀 Features

- 🔁 **Email-to-Issue Automation**: Seamlessly transforms incoming emails into structured Redmine issues.
- 🤖 **Intelligent Task Classification**: Uses NLP to auto-route tasks with a 30% boost in accuracy.
- 🐳 **Containerized Deployment**: Dockerized architecture ensures easy deployment and portability.
- 💸 **Cost-Efficient**: Replaces expensive third-party services with a lightweight, in-house solution.

## 🛠 Tech Stack

- **Backend**: Python
- **APIs**: Microsoft Graph API, Redmine REST API
- **NLP**: Scikit-learn / spaCy (customizable)
- **Containerization**: Docker, Docker Compose

## 📦 Project Structure

```
.
├── src/
│   ├── main.py
│   ├── email_reader.py
│   ├── redmine_handler.py
│   ├── monitor_sender.py
│   └── config/
├── logs/              # Ignored via .gitignore
├── Dockerfile
├── docker-compose.yml
├── .env               # Ignored via .gitignore
├── README.md
└── requirements.txt
```

## ⚙️ Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/WUUUYT/redmine-email-system.git
cd #####
```

### 2. Configure environment variables and configurations

Create a `.env` file based on `.env.example`:

```env
REDMINE_API_KEY=your_api_key
REDMINE_URL=https://your.redmine.url
```

Create a `config.json` file based on `config_example.json``

```
{
    "projects": {
        "Unique ID#": {
            "name": "",
            "email": "1223@example.com",
            "cache_file": "data/1223.bin",
            "enabled": true,
            "createdefault": {
                "status_id": 1,
                "tracker_id": 2,
                "priority_id": 2,
                "assigned_to_id": null,
                "business_unit": [4] },
            "emailignore": {
                "startwith": ["Automatic reply"],
                "contain": ["new"],
                "endwith": []}}},
    "reminderconfig": {
        "status_change": true,
        "priority_change": false,
        "assignee_change": false,
        "tracker_change": false,
        "notes_change": false},
    "client_ID": "",
    "tenant_ID": "",
    "check_interval": 1}
```
You could arrange multiple services for different projects here. The Unique ID# is the last part of the URL, the email is the service emails scheduled for this service. `Cache_file` should be filled with a bin file to store the refresh key to visit the Microsoft Azure service.

We also provide a service that you can custom the format of the email subject such that you don't get notifications from this group of emails.

In the last part, you can edit the kind of updates you want to receive.

Client ID and tenant ID are necessary information you should get from your admin.

Check interval is the time interval (no. of minutes) that the program runs.

> ✅ **Important**: Never commit the `.env` file. It's already in `.gitignore`.

### 3. Build & Run with Docker

```bash
docker-compose up --build
```

## 🛡 Security

- Secrets managed in `.env` (excluded from version control)
- OAuth 2.0 via Microsoft Graph API
- No hard-coded credentials

## 📄 License

[MIT](LICENSE)

---

## 🙋‍♂️ Acknowledgments

- Microsoft Graph API
- Redmine REST API
- Open-source NLP tools
