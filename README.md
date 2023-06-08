# Github Email Collector

Collect the email address of users affiliated to a given repository

## Installation
### From PyPi

```python
pip install github-email-collector
```

### As a submodule

```
git submodule add https://github.com/LucBerge/github_email_collector.git
git submodule update --init
```

## Usage

From your python script
```python
from github_email_collector import EmailCollector

email_collector = EmailCollector("MY_GITHUB_TOKEN", "owner/repo")
emails = email_collector.get_emails()
print(emails)
```
