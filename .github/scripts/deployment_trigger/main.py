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
DEPLOYMENTS_PROJECT = os.environ.get("DEPLOYMENTS_PROJECT")
DEPLOYMENTS_REPO_NAME = os.environ.get("DEPLOYMENTS_REPO_NAME")
DEPLOYMENTS_DEV_BRANCH = os.environ.get("DEPLOYMENTS_DEV_BRANCH")
DEPLOYMENTS_DEV_CONFIG_FOLDER = os.environ.get("DEPLOYMENTS_DEV_CONFIG_FOLDER")
#############
# Variables #
#############
clone_folder = "./git-repo"


#######################
# ENV variables check #
#######################
required_env_variables = ["APP_NAME", "NEW_VERSION", "DEPLOYMENTS_PROJECT", "DEPLOYMENTS_REPO_NAME",
                          "DEPLOYMENTS_DEV_BRANCH", "DEPLOYMENTS_DEV_CONFIG_FOLDER"]
for variable in required_env_variables:
    if variable not in os.environ or os.environ.get(variable) == "":
        print("ERROR! {} variable is not set. Exiting...".format(variable))
        sys.exit(1)

############################
# Cloning deployments repo #
############################
print("Creating clone folder ...")
os.system("mkdir {}".format(clone_folder))
print("Cloning deployments repo to {} ...".format(clone_folder))
DEPLOYMENTS_REPO = "git@github.com:{}/{}.git".format(DEPLOYMENTS_PROJECT, DEPLOYMENTS_REPO_NAME)
deployments_repo = Repo.clone_from(DEPLOYMENTS_REPO, "{}".format(clone_folder),
                                   env={"GIT_SSH_COMMAND": 'ssh -o StrictHostKeyChecking=no '})
deployments_repo.git.config("--global", "user.email", "github_bot@example.com")
deployments_repo.git.config("--global", "user.name", "GitHub BOT")


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
with open('{}/{}/{}.yml'.format(clone_folder, DEPLOYMENTS_DEV_CONFIG_FOLDER, APP_NAME)) as f:
    deployments = yaml.load(f, Loader=yaml.FullLoader)
    if NEW_VERSION == deployments["artifact_version"]:
        print("There is no change in version. Exiting...")
        sys.exit(1)
    else:
        deployments["artifact_version"] = NEW_VERSION

############################
# Saving changes to a file #
############################
with open('{}/{}/{}.yml'.format(clone_folder, DEPLOYMENTS_DEV_CONFIG_FOLDER, APP_NAME), 'w') as f:
    data = yaml.dump(deployments, f)

###################
# Staging changes #
###################
deployments_repo.git.add('{}/{}.yml'.format(DEPLOYMENTS_DEV_CONFIG_FOLDER, APP_NAME))

#####################
# Creating a commit #
#####################
deployments_repo.git.commit("-m", "auto: DEV: Updating {} to the new version -> {}".format(APP_NAME, NEW_VERSION))

#######################
# Pushing the changes #
#######################
print("Pushing changes ...")
deployments_repo.git.push("--set-upstream", "origin", DEPLOYMENTS_DEV_BRANCH)
