from release2gitcode.core.github import parse_github_release_url
from release2gitcode.core.gitcode import parse_gitcode_repo_url


def test_parse_github_release_tag_url() -> None:
    owner, repo, tag = parse_github_release_url("https://github.com/octo/demo/releases/tag/v1.2.3")
    assert (owner, repo, tag) == ("octo", "demo", "v1.2.3")


def test_parse_gitcode_repo_url() -> None:
    ref = parse_gitcode_repo_url("https://gitcode.com/acme/project.git")
    assert ref.owner == "acme"
    assert ref.repo == "project"
    assert ref.repo_url == "https://gitcode.com/acme/project"
