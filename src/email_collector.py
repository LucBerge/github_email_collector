import github
from github import NamedUser
import time
import requests
import re

class GithubUser():

    DEFAULT_REPO_TRIES = 2
    DEFAULT_COMMIT_TRIES = 2

    REGEX_PATCH_EMAIL = r'From: .*<(.+?)>'

    def __init__(self, user):
        self._user = user
        self._email = None

    def get_email(self)->str:
        try:
            if self._user.email is not None:
                self._email = self._user.email
            else:
                # Get repos
                repo_tries = self.DEFAULT_REPO_TRIES
                for repo in self._user.get_repos(type="owner"):

                    # If the repo is not a fork
                    if not repo.fork:

                        # Get commits
                        commit_tries = self.DEFAULT_COMMIT_TRIES
                        for commit in repo.get_commits(author=self._user):
                            # Get patch
                            patch = requests.get(commit.html_url + ".patch").text
                            emails = re.findall(self.REGEX_PATCH_EMAIL, patch)

                            # If found a email
                            if len(emails):
                                self._email = emails[0]
                                return self._email

                            # If was last try, skip to next repo
                            commit_tries -= 1
                            if commit_tries == 0:
                                break

                        # If was last try, skip to next user
                        repo_tries -= 1
                        if repo_tries == 0:
                            break

        except github.GithubException:
            pass

        return self._email

class EmailCollector:

    SLEEP_TIME = 0.01
    OVER_RATE_LIMIT_SLEEP_TIME = 60*60
    MAX_RESULTS_PER_PAGE = 40000
    RATE_LIMIT = 4900

    def __init__(self, token: str, repo: str):
        g = github.Github(token, per_page=self.MAX_RESULTS_PER_PAGE)
        self._repo = g.get_repo(repo)
        self._requests = 0
        self._users = {}

    def __add_user(self, user: NamedUser)->None:
        self._users[user.login] = GithubUser(user)

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
        print(f"Getting users for {self._repo.full_name}...")

        # If users not collected
        if len(self._users) == 0:
            self.__add_owner()
            self.__add_contributors()
            self.__add_forks()
            self.__add_stargazers()
            self.__add_watchers()
            self.__add_issues()

        print(f"Found {len(self._users)} unique users")
        return self._users

    def get_emails(self)->tuple[dict, float]:
        self.get_users()

        print(f"Getting email addresses for {self._repo.full_name}...")
        emails = {}

        i = 1
        print(f"0/{len(self._users)}", flush=True, end='\r')
        for login, user in self._users.items():

            email = user.get_email()
            if email is not None:
                emails[login] = email

            print(f"{i}/{len(self._users)} | {len(emails)} success | {i-len(emails)} fails", flush=True, end='\n' if i==len(self._users) else '\r')
            i+=1

        print(f"Found {len(emails)} email addresses")
        success_rate = round(len(emails)*100/len(self._users), 2)
        print(f"Success rate is {success_rate}%")
        return emails, success_rate
