#!/usr/bin/env python3

import logging
import tempfile
import os
from pathlib import Path
import json
import calendar
import time
import shutil
import yaml

from github import Github
from github.GithubException import UnknownObjectException, RateLimitExceededException
import git
from jinja2 import Environment, FileSystemLoader, select_autoescape

logging.basicConfig(level=logging.INFO)

# We want the root
here = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

env = Environment(
    autoescape=select_autoescape(["html"]), loader=FileSystemLoader("templates")
)

# do not clone LFS files
os.environ["GIT_LFS_SKIP_SMUDGE"] = "1"
g = Github(os.environ["GITHUB_TOKEN"])
repos = []

core_rate_limit = g.get_rate_limit().core


def read_yaml(filename):
    with open(filename, "r") as fd:
        content = yaml.load(fd, Loader=yaml.FullLoader)
    return content


class Repo:
    data_format = 2

    def __init__(self, github_repo, readme, filenames):
        for attr in [
            "full_name",
            "description",
            "stargazers_count",
            "subscribers_count",
        ]:
            setattr(self, attr, getattr(github_repo, attr))

        self.topics = github_repo.get_topics()
        self.updated_at = github_repo.updated_at.timestamp()
        self.filenames = list(filenames)

        try:
            self.latest_release = github_repo.get_latest_release().tag_name
        except UnknownObjectException:
            # no release
            self.latest_release = None

        if readme is not None:
            self.readme = g.render_markdown(readme)
        self.data_format = Repo.data_format


def rate_limit_wait():
    curr_timestamp = calendar.timegm(time.gmtime())
    reset_timestamp = calendar.timegm(core_rate_limit.reset.timetuple())
    # add 5 seconds to be sure the rate limit has been reset
    sleep_time = max(0, reset_timestamp - curr_timestamp) + 5
    logging.warning(f"Rate limit exceeded, waiting {sleep_time} seconds")
    time.sleep(sleep_time)


def call_rate_limit_aware(func):
    while True:
        try:
            return func()
        except RateLimitExceededException:
            rate_limit_wait()


def call_rate_limit_aware_decorator(func):
    def inner(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except RateLimitExceededException:
                rate_limit_wait()

    return inner


def store_data():
    repos.sort(key=lambda repo: repo["stargazers_count"])

    # Save the js data ready to go, and data for jekyll
    datapath = os.path.join(here, "assets", "js", "repos.js")
    with open(datapath, "w") as out:
        print(env.get_template("repos.js").render(data=repos), file=out)

    # Also save to yaml in data folder
    datapath = os.path.join(here, "_data", "repos.yml")
    results = {}
    for repo in repos:
        results[repo["full_name"]] = repo
    with open(datapath, "w") as out:
        yaml.dump(results, out)


@call_rate_limit_aware_decorator
def combine_results(code_search):
    """
    Given a code search result, organize by repos
    """
    byrepo = {}
    lookup = {}
    files = {}

    for i, filename in enumerate(code_search):

        # attempt to not trigger abuse mechanism
        time.sleep(0.5)
        repo = filename.repository

        # skip spack_yaml.py, and github workflows
        if os.path.basename(filename.path) == "spack_yaml.py":
            continue

        # Do not include non yaml files
        if not filename.path.endswith("yaml") and not filename.path.endswith("yml"):
            continue

        # skip GitHub workflows
        elif ".github/workflows" in filename.path:
            continue

        # skip examples in spack docs
        if "lib/spack/docs" in filename.path:
            continue

        if repo.full_name not in byrepo:
            byrepo[repo.full_name] = set()
            lookup[repo.full_name] = repo
        byrepo[repo.full_name].add(filename.path)
    return byrepo, lookup


def validate_spackyaml(filename):
    """
    Ensure that a spack.yaml file has a spack or env directive
    """
    try:
        with open(filename, "r") as fd:
            data = yaml.load(fd, Loader=yaml.FullLoader)
            if "env" not in data and "spack" not in data:
                return False
            return True
    except yaml.YAMLError as exc:
        return False


def main():
    """
    Entrypoint to catalog generation
    """
    skips = set(l.strip() for l in open("skips.txt", "r"))

    # Don't parse the vsoch/spack-changes repository!
    code_search = g.search_code("spack filename:spack.yaml+-user:vsoch", sort="indexed")

    # Create a directory structure with spack.yaml files
    data_dir = os.path.join(here, "_stacks")

    # Consolidate filenames by repository
    byrepo, lookup = combine_results(code_search)
    total_count = len(byrepo)

    for i, reponame in enumerate(byrepo):

        # List of files
        files = byrepo[reponame]
        repo = lookup[reponame]
        if i % 10 == 0:
            logging.info(f"{i} of {total_count} results done")

        repo_dir = os.path.join(data_dir, repo.full_name)
        if repo.full_name in skips:
            continue

        logging.info(f"Processing {repo.full_name}.")

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)

            # Create the repo directory
            if not os.path.exists(repo_dir):
                os.makedirs(repo_dir)

            # clone main branch
            try:
                git.Repo.clone_from(repo.clone_url, str(tmp), depth=1)
            except git.GitCommandError:
                continue

            # We will update files if a file doesn't exist or is invalid
            updated_files = []

            # For each spack yaml, validate
            for filename in files:
                spackyaml = tmp / filename
                spackyamldir = os.path.dirname(spackyaml)
                if not spackyaml.exists():
                    continue

                savepath = os.path.join(repo_dir, filename)
                savedir = os.path.dirname(savepath)
                if not os.path.exists(savedir):
                    os.makedirs(savedir)

                # Ensure this is a spack.yaml file, it must have spack or env
                if not validate_spackyaml(spackyaml):
                    continue

                # TODO: we could validate or generate Dockerfile here
                shutil.copyfile(str(spackyaml), savepath)
                updated_files.append(filename)

            # Look for a readme in the folder, then root
            readme = None
            readme_path = tmp / "README.md"
            if readme_path.exists():
                with open(readme_path, "r") as f:
                    readme = f.read()

        # Don't add repos without any spack.yaml files
        if not updated_files:
            continue

        call_rate_limit_aware(
            lambda: repos.append(Repo(repo, readme, updated_files).__dict__)
        )
        # repos.append(Repo(repo, readme, updated_files).__dict__)

        if len(repos) % 20 == 0:
            logging.info("Storing intermediate results.")
            store_data()

    # one final save
    store_data()


if __name__ == "__main__":
    main()
