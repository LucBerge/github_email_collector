from github import NamedUser, Github
from github.GithubException import RateLimitExceededException
from datetime import datetime
import requests
import re
import time
import traceback

class GithubUser():

    DEFAULT_COMMITS_LIMIT = 4
    NOREPLY_SUBSTRING = "noreply"

    REGEX_PATCH_EMAIL = r'<(.+?)>'

    def __init__(self, client: Github, user: NamedUser):
        self._client = client
        self._user = user
        self._email = None
        self._last_activity = None

    @property
    def email(self)->str:
        if self._email is None:
            self._email = self.get_email()
        return self._email

    @property
    def last_activity(self)->datetime:
        if self._last_activity is None:
            self._last_activity = self.get_last_activity()
        return self._last_activity

    def get_email(self)->str:
        try:
            # If user has public email address
            if self._user.email is not None:
                return self._user.email
            else:
                # Get first commits
                commits = self._client.search_commits(
                    query = f'author:{self._user.login} sort:author-date-asc'
                )

                def get_length():
                    return commits.totalCount

                length = self._perform_request(get_length)
                # If has at least one commit
                if length:
                    # For each commit
                    for commit in commits[:self.DEFAULT_COMMITS_LIMIT]:
                        # Get patch
                        _, data = self._client._Github__requester.requestMultipartAndCheck("GET", commit.html_url + ".patch")
                        emails = re.findall(self.REGEX_PATCH_EMAIL, data.get("data"))

                        # If found email address
                        if len(emails):
                            # If does not contain noreply
                            if not self.NOREPLY_SUBSTRING in emails[0]:
                                return emails[0]

        except Exception:
            traceback.print_exc()

        return None

    def get_last_activity(self)->datetime:
        commits = self._client.search_commits(
            query = f'author:{self._user.login} sort:author-date-desc'
        )
        if commits.totalCount:
            return commits[0].commit.author.date
        return None

    def _perform_request(self, request_method):
        try:
            return request_method()
        except RateLimitExceededException:
            now = datetime.now()
            end = datetime.fromtimestamp(self._client.rate_limiting_resettime)
            seconds = round((end - now).total_seconds(), 0) + 1
            print(f"Rate limit reached ! Waiting {seconds} seconds...")
            time.sleep(seconds)
            return request_method()

class EmailCollector:

    SLEEP_TIME = 0.01
    OVER_RATE_LIMIT_SLEEP_TIME = 60*60
    MAX_RESULTS_PER_PAGE = 40000
    RATE_LIMIT = 4900

    def __init__(self, token: str, repo: str):
        self._client = Github(token, per_page=self.MAX_RESULTS_PER_PAGE)
        self._repo = self._client.get_repo(repo)
        self._requests = 0
        self._users = {}

    def __add_user(self, user: NamedUser)->None:
        self._users[user.login] = GithubUser(self._client, user)

    def __add_elements(self, elements, mapper)->int:
        print(f"0/{elements.totalCount}", flush=True, end="\r")

        # For each contributor
        for i in range(elements.totalCount):

            print(f"{i+1}/{elements.totalCount}", flush=True, end='\n' if i+1==elements.totalCount else '\r')
            # Add the user
            self.__add_user(mapper(elements[i]))
            self._requests = self._requests+1

        return elements.totalCount

    def __add_owner(self)->int:
        print("Getting repo owner...", flush=True)
        self.__add_user(self._repo.owner)
        return 1

    def __add_contributors(self)->int:
        print("Getting contributors...", flush=True)
        return self.__add_elements(self._repo.get_contributors(), lambda c: c)

    def __add_forks(self)->int:
        print("Getting forks...", flush=True)
        return self.__add_elements(self._repo.get_forks(), lambda f: f.owner)

    def __add_stargazers(self)->int:
        print("Getting stargazers...", flush=True)
        return self.__add_elements(self._repo.get_stargazers(), lambda s: s)

    def __add_watchers(self)->int:
        print("Getting watchers...", flush=True)
        return self.__add_elements(self._repo.get_watchers(), lambda w: w)

    def __add_issues(self)->int:
        print("Getting issues...", flush=True)
        return self.__add_elements(self._repo.get_issues(), lambda i: i.user)

    def get_users(self)->dict:
        self._users = {}

        # STEP 1 - GET USERS

        print(f"Getting users for {self._repo.full_name}...")
        self.__add_owner()
        self.__add_contributors()
        self.__add_forks()
        self.__add_stargazers()
        self.__add_watchers()
        self.__add_issues()
        print(f"Found {len(self._users)} unique users")

        # STEP 2 - ORDERING USERS

        #print(f"Ordering users from the most active to the less active {self._repo.full_name}...")
        #print(self._users)
        #print("=============================")
        #print(dict(sorted(self._users.items(), key=lambda u: u[1].last_activity)))

        return self._users

    def get_emails(self)->tuple[dict, float]:

        # STEP 1 - GET USERS

        self.get_users()

        # STEP 2 - GET EMAILS

        print(f"Getting email addresses for {self._repo.full_name}...")
        emails = {}

        i = 1
        print(f"0/{len(self._users)}", flush=True, end='\r')
        for login, user in self._users.items():

            if user.email is not None:
                emails[login] = user.email

            print(f"{i}/{len(self._users)} | {len(emails)} success | {i-len(emails)} fails", flush=True, end='\n' if i==len(self._users) else '\r')
            i+=1

        # STEP 4 - DISPLAY RESULTS

        print(f"Found {len(emails)} email addresses")
        success_rate = round(len(emails)*100/len(self._users), 2)
        print(f"Success rate is {success_rate}%")
        return emails, success_rate
