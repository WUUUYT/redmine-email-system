FROM python:3.13-slim

RUN apt-get update && apt-get install -y cron \
    && rm -rf /var/lib/apt/lists/*

# Setting working directory
WORKDIR /app

# Install all the python requirements
COPY requirements.txt .
RUN pip install -r /app/requirements.txt

# Copy all the files under this folder to container
COPY . .

RUN echo "* * * * * root bash -c 'cd /app && /usr/local/bin/python src/main.py' >> /var/log/redmineticket/redmineticket.log 2>&1" > /etc/cron.d/my-python-job \
    && chmod 0644 /etc/cron.d/my-python-job \
    && mkdir -p /var/log/redmineticket \
    && touch /var/log/redmineticket/redmineticket.log

CMD ["cron", "-f"]
