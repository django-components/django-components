import logging
import secrets
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import yaml
from github import Github
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings

github_graphql_url = "https://api.github.com/graphql"

get_commits_query = """
query Q($after: String) {
  repository(name: "django-components", owner: "EmilStenstrom") {
    defaultBranchRef {
      target {
        ... on Commit {
          history(first: 100, after: $after) {
            edges {
              cursor
              node {
                message
                committedDate
                author {
                  user {
                    login
                    avatarUrl
                    url
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


class Settings(BaseSettings):
    github_token: SecretStr
    github_repository: str
    httpx_timeout: int = 30
    sleep_interval: int = 5


class User(BaseModel):
    login: str
    avatarUrl: str
    url: str


class Author(BaseModel):
    user: User | None = None


class CommitNode(BaseModel):
    message: str
    committedDate: datetime
    author: Author


class CommitEdge(BaseModel):
    cursor: str
    node: CommitNode


class CommitsHistory(BaseModel):
    edges: list[CommitEdge]


class CommitsTarget(BaseModel):
    history: CommitsHistory


class CommitsBranch(BaseModel):
    target: CommitsTarget


class CommitsRepository(BaseModel):
    defaultBranchRef: CommitsBranch


class CommitsResponseData(BaseModel):
    repository: CommitsRepository


class CommitsResponse(BaseModel):
    data: CommitsResponseData


def get_graphql_response(
    *,
    settings: Settings,
    query: str,
    after: str | None = None,
) -> dict[str, Any]:
    """Make a GraphQL request to GitHub API and return the response."""
    headers = {"Authorization": f"token {settings.github_token.get_secret_value()}"}
    variables = {"after": after}
    response = httpx.post(
        github_graphql_url,
        headers=headers,
        timeout=settings.httpx_timeout,
        json={"query": query, "variables": variables, "operationName": "Q"},
    )
    if response.status_code != 200:
        logging.error(f"Response was not 200, after: {after}")
        logging.error(response.text)
        raise RuntimeError(response.text)
    data = response.json()
    if "errors" in data:
        logging.error(f"Errors in response, after: {after}")
        logging.error(data["errors"])
        logging.error(response.text)
        raise RuntimeError(response.text)
    return data


def get_graphql_pr_edges(*, settings: Settings, after: str | None = None) -> list[CommitEdge]:
    """
    Fetch pull request edges from GitHub GraphQL API.
    """
    data = get_graphql_response(settings=settings, query=get_commits_query, after=after)
    graphql_response = CommitsResponse.model_validate(data)
    return graphql_response.data.repository.defaultBranchRef.target.history.edges


def get_contributors(settings: Settings) -> tuple[Counter, dict[str, User]]:
    """
    Analyze pull requests to identify contributors.
    """
    nodes = []
    edges = get_graphql_pr_edges(settings=settings)
    while edges:
        # Get all data.
        for edge in edges:
            nodes.append(edge.node)
        last_edge = edges[-1]
        edges = get_graphql_pr_edges(settings=settings, after=last_edge.cursor)

    contributors = Counter()
    users: dict[str, User] = {}
    for commit in nodes:
        user = commit.author.user
        if user:
            contributors[user.login] += 1
            if user.login not in users:
                users[user.login] = user

    return contributors, users


def update_content(*, content_path: Path, new_content: Any) -> bool:
    old_content = content_path.read_text(encoding="utf-8")

    new_content = yaml.dump(new_content, sort_keys=False, width=200, allow_unicode=True)
    if old_content == new_content:
        logging.info(f"The content hasn't changed for {content_path}")
        return False
    content_path.write_text(new_content, encoding="utf-8")
    logging.info(f"Updated {content_path}")
    return True



def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    logging.info(f"Using config: {settings.model_dump_json()}")
    g = Github(settings.github_token.get_secret_value())
    repo = g.get_repo(settings.github_repository)
    contributors_data, users = get_contributors(settings=settings)
    maintainers_logins = {
        "EmilStenstrom",
        "JuroOravec",
    }
    bot_logins = {
        "dependabot[bot]",
        "github-actions[bot]",
        "pre-commit-ci[bot]",
    }
    skip_users = maintainers_logins | bot_logins
    maintainers = []
    for login in maintainers_logins:
        user = users[login]
        maintainers.append(
            {
                "login": login,
                "avatarUrl": user.avatarUrl,
                "url": user.url,
            }
        )
    contributors = []
    for contributor, count in contributors_data.most_common():
        if contributor in skip_users:
            continue
        user = users[contributor]
        contributors.append(
            {
                "login": user.login,
                "avatarUrl": user.avatarUrl,
                "url": user.url,
                "count": count,
            }
        )
    people = {
        "maintainers": maintainers,
        "contributors": contributors,
    }
    people_path = Path('../docs/django_components_people/people.yml')
    updated = update_content(content_path=people_path, new_content=people)

    if not updated:
        logging.info("The data hasn't changed, finishing.")
        return

    logging.info("Setting up GitHub Actions git user")
    subprocess.run(["git", "config", "user.name", "github-actions"], check=True)
    subprocess.run(
        ["git", "config", "user.email", "github-actions@github.com"], check=True
    )
    branch_name = f"django-components-people-{secrets.token_hex(4)}"
    logging.info(f"Creating a new branch {branch_name}")
    subprocess.run(["git", "checkout", "-b", branch_name], check=True)
    logging.info("Adding updated file")
    subprocess.run(["git", "add", str(people_path)], check=True)
    logging.info("Committing updated file")
    message = "👥 Update FastAPI People - Experts"
    subprocess.run(["git", "commit", "-m", message], check=True)
    logging.info("Pushing branch")
    subprocess.run(["git", "push", "origin", branch_name], check=True)
    logging.info("Creating PR")
    pr = repo.create_pull(title=message, body=message, base="master", head=branch_name)
    logging.info(f"Created PR: {pr.number}")
    logging.info("Finished")


if __name__ == "__main__":
    main()
