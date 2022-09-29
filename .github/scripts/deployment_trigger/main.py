import os
import yaml
import sys
from git import Repo
import requests
import json


#################
# ENV Variables #
#################
APP_NAME = os.environ.get("APP_NAME")
NEW_VERSION = os.environ.get("NEW_VERSION")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
DEPLOYMENTS_REPO = os.environ.get("DEPLOYMENTS_REPO")
DEPLOYMENTS_DEV_BRANCH = os.environ.get("DEPLOYMENTS_DEV_BRANCH")
DEPLOYMENTS_DEV_CONFIG_PATH = os.environ.get("DEPLOYMENTS_DEV_CONFIG_PATH")
DEPLOYMENTS_MAIN_BRANCH = os.environ.get("DEPLOYMENTS_MAIN_BRANCH")
#############
# Variables #
#############
clone_folder = "./git-repo"
deployment_git_project = DEPLOYMENTS_REPO.split("/")[-2]
deployment_git_repo_name = DEPLOYMENTS_REPO.split("/")[-1].replace(".git", "")


########################################################################
# Creates the pull request for the head_branch against the base_branch #
########################################################################
def create_pull_request(project_name, repo_name, title, description, head_branch, base_branch, git_token):
    # https://github.com/api/v3/repos/{0}/{1}/pulls for Enterprise
    git_pulls_api = "https://api.github.com/repos/{0}/{1}/pulls".format(
        project_name,
        repo_name)
    headers = {
        "Authorization": "token {0}".format(git_token),
        "Content-Type": "application/json"}

    payload = {
        "title": title,
        "body": description,
        "head": head_branch,
        "base": base_branch,
    }

    r = requests.post(
        git_pulls_api,
        headers=headers,
        data=json.dumps(payload))

    if not r.ok:
        print("Request Failed: {0}".format(r.text))
        sys.exit(1)


#####################################
# Checks if such pull request exist #
#####################################
def check_pull_request_exist(project_name, repo_name, title, description, head_branch, base_branch, git_token):
    pr_exist = False
    # https://github.com/api/v3/repos/{0}/{1}/pulls for Enterprise
    git_pulls_api = "https://api.github.com/repos/{0}/{1}/pulls".format(
        project_name,
        repo_name)
    headers = {
        "Authorization": "token {0}".format(git_token),
        "Content-Type": "application/json"}

    r = requests.get(
        git_pulls_api,
        headers=headers)

    pull_requests_list = json.loads(r.text)
    for pr in pull_requests_list:
        if pr['head']['ref'] == head_branch and pr['base']['ref'] == base_branch:
            pr_exist = True
    return pr_exist


#######################
# ENV variables check #
#######################
required_env_variables = ["APP_NAME", "NEW_VERSION", "GITHUB_TOKEN", "DEPLOYMENTS_REPO", "DEPLOYMENTS_DEV_BRANCH",
                          "DEPLOYMENTS_DEV_CONFIG_PATH", "DEPLOYMENTS_MAIN_BRANCH"]
for variable in required_env_variables:
    if variable not in os.environ:
        print("ERROR! {} variable is not set. Exiting...".format(variable))
        sys.exit(1)


############################
# Cloning deployments repo #
############################
print("Creating clone folder ...")
os.system("mkdir {}".format(clone_folder))
print("Cloning deployments repo to {} ...".format(clone_folder))
DEPLOYMENTS_REPO = "https://{}:x-oauth-basic@github.com/{}/{}".format(GITHUB_TOKEN, deployment_git_project,
                                                                      deployment_git_repo_name)
deployments_repo = Repo.clone_from(DEPLOYMENTS_REPO, "{}".format(clone_folder))

#########################################
# Checking out to a new/existing branch #
#########################################
branch_exist = False
for ref in deployments_repo.references:
    if "origin/{}".format(DEPLOYMENTS_DEV_BRANCH) == ref.name:
        branch_exist = True
if not branch_exist:
    print("Creating a new branch: {} ...".format(DEPLOYMENTS_DEV_BRANCH))
    deployments_repo.git.checkout('-b', DEPLOYMENTS_DEV_BRANCH)
else:
    print("Branch {} is already exist ...".format(DEPLOYMENTS_DEV_BRANCH))
    deployments_repo.git.checkout(DEPLOYMENTS_DEV_BRANCH)

#########################
# Setting a new version #
#########################
print("Updating {} version in deployments file to {} ...".format(APP_NAME, NEW_VERSION))
with open('{}/{}'.format(clone_folder, DEPLOYMENTS_DEV_CONFIG_PATH)) as f:
    deployments = yaml.load(f, Loader=yaml.FullLoader)
    if NEW_VERSION == deployments[APP_NAME]["artifact_version"]:
        print("There is no change in version. Exiting...")
        sys.exit(1)
    else:
        deployments[APP_NAME]["artifact_version"] = NEW_VERSION

############################
# Saving changes to a file #
############################
with open('{}/{}'.format(clone_folder, DEPLOYMENTS_DEV_CONFIG_PATH), 'w') as f:
    data = yaml.dump(deployments, f)

###################
# Staging changes #
###################
deployments_repo.git.add('{}'.format(DEPLOYMENTS_DEV_CONFIG_PATH))

#####################
# Creating a commit #
#####################
deployments_repo.git.commit("-m", "\"auto: Updating {} to the new version -> {}\"".format(APP_NAME, NEW_VERSION))

#######################
# Pushing the changes #
#######################
print("Pushing changes ...")
deployments_repo.git.push("--set-upstream", "origin", DEPLOYMENTS_DEV_BRANCH)

#########################
# Creating Pull Request #
#########################
pull_request_exist = check_pull_request_exist(
    deployment_git_project,
    deployment_git_repo_name,
    "AUTO: Versions update in DEV environment",
    "AUTO: Versions update in DEV environment",
    DEPLOYMENTS_DEV_BRANCH,
    DEPLOYMENTS_MAIN_BRANCH,
    GITHUB_TOKEN
)
if pull_request_exist:
    print("Pull request is already exist. Skipping...")
else:
    print("Creating a Pull Request ...")
    create_pull_request(
        deployment_git_project,
        deployment_git_repo_name,
        "AUTO: Versions update in DEV environment",
        "AUTO: Versions update in DEV environment",
        DEPLOYMENTS_DEV_BRANCH,
        DEPLOYMENTS_MAIN_BRANCH,
        GITHUB_TOKEN
    )
