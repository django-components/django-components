"""
This logic is inspired by that of @tiangolo's (FastAPI People)
[FastAPI people script](https://github.com/fastapi/fastapi/blob/master/scripts/people.py).
"""

import logging
import secrets
import shutil
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
import yaml  # type: ignore[import-untyped]
from github import Github
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

github_graphql_url = "https://api.github.com/graphql"

prs_query = """
query Q($after: String) {
  repository(name: "django-components", owner: "EmilStenstrom") {
    pullRequests(first: 100, after: $after) {
      edges {
        cursor
        node {
          author {
            login
            avatarUrl
            url
          }
          title
          createdAt
          state
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


class Author(BaseModel):
    login: str
    avatarUrl: str  # noqa: N815
    url: str


class PullRequestNode(BaseModel):
    author: Union[Author, None] = None
    title: str
    createdAt: datetime  # noqa: N815
    state: str


class PullRequestEdge(BaseModel):
    cursor: str
    node: PullRequestNode


class PullRequests(BaseModel):
    edges: List[PullRequestEdge]


class PRsRepository(BaseModel):
    pullRequests: PullRequests  # noqa: N815


class PRsResponseData(BaseModel):
    repository: PRsRepository


class PRsResponse(BaseModel):
    data: PRsResponseData


def get_graphql_response(
    *,
    settings: Settings,
    query: str,
    after: Optional[str] = None,
) -> Dict[str, Any]:
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
        logger.error("Response was not 200, after: %s", after)
        logger.error(response.text)
        raise RuntimeError(response.text)
    data = response.json()
    if "errors" in data:
        logger.error("Errors in response, after: %s", after)
        logger.error(data["errors"])
        logger.error(response.text)
        raise RuntimeError(response.text)
    return data


def get_graphql_pr_edges(*, settings: Settings, after: Optional[str] = None) -> List[PullRequestEdge]:
    """Fetch pull request edges from GitHub GraphQL API."""
    data = get_graphql_response(settings=settings, query=prs_query, after=after)
    graphql_response = PRsResponse.model_validate(data)
    return graphql_response.data.repository.pullRequests.edges


def get_contributors(settings: Settings) -> Tuple[Counter, Dict[str, Author]]:
    """Analyze pull requests to identify contributors."""
    nodes = []
    edges = get_graphql_pr_edges(settings=settings)
    while edges:
        # Get all data.
        for edge in edges:
            nodes.append(edge.node)
        last_edge = edges[-1]
        edges = get_graphql_pr_edges(settings=settings, after=last_edge.cursor)

    contributors: Counter[str] = Counter()
    authors: Dict[str, Author] = {}
    for pr in nodes:
        author = pr.author
        if author and pr.state == "MERGED":
            contributors[author.login] += 1
            if author.login not in authors:
                authors[author.login] = author

    return contributors, authors


def update_content(*, content_path: Path, new_content: Any) -> bool:
    old_content = content_path.read_text(encoding="utf-8")

    new_content = yaml.dump(new_content, sort_keys=False, width=200, allow_unicode=True)
    if old_content == new_content:
        logger.info("The content hasn't changed for %s", content_path)
        return False
    content_path.write_text(new_content, encoding="utf-8")
    logger.info("Updated %s", content_path)
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    git_exe = shutil.which("git")
    if not git_exe:
        raise RuntimeError("Cannot find git executable")

    settings = Settings()
    logger.info("Using config: %s", settings.model_dump_json())
    g = Github(settings.github_token.get_secret_value())
    repo = g.get_repo(settings.github_repository)
    contributors_data, users = get_contributors(settings=settings)
    maintainers_logins = {
        "EmilStenstrom",
        "JuroOravec",
    }
    bot_logins = {
        "dependabot",
        "github-actions",
        "pre-commit-ci",
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
    people_path = Path("../community/people.yml")
    updated = update_content(content_path=people_path, new_content=people)

    if not updated:
        logger.info("The data hasn't changed, finishing.")
        return

    logger.info("Setting up GitHub Actions git user")
    subprocess.run([git_exe, "git", "config", "user.name", "github-actions"], check=True)
    subprocess.run([git_exe, "git", "config", "user.email", "github-actions@github.com"], check=True)
    branch_name = f"django-components-people-{secrets.token_hex(4)}"
    logger.info("Creating a new branch %s", branch_name)
    subprocess.run([git_exe, "git", "checkout", "-b", branch_name], check=True)
    logger.info("Adding updated file")
    subprocess.run([git_exe, "git", "add", str(people_path)], check=True)
    logger.info("Committing updated file")
    message = "👥 Update FastAPI People - Experts"
    subprocess.run([git_exe, "git", "commit", "-m", message], check=True)
    logger.info("Pushing branch")
    subprocess.run([git_exe, "git", "push", "origin", branch_name], check=True)
    logger.info("Creating PR")
    pr = repo.create_pull(title=message, body=message, base="master", head=branch_name)
    logger.info("Created PR: %s", pr.number)
    logger.info("Finished")


if __name__ == "__main__":
    main()
