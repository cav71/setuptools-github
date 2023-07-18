from setuptools_github import scm


def test_extract_beta_branches(git_project_factory):
    "test the branch and tag extraction function"
    from pygit2 import Repository

    repo = git_project_factory("test_check_version-repo").create("0.0.0")
    repo1 = git_project_factory("test_check_version-repo1").create(clone=repo)

    repo.branch("beta/0.0.3")
    repo(["tag", "-m", "release", "release/0.0.3"])
    repo.branch("beta/0.0.4")
    repo(["tag", "-m", "release", "release/0.0.4"])
    repo1.branch("beta/0.0.2")

    project = git_project_factory().create(clone=repo)
    project.branch("beta/0.0.1", "origin/master")
    project.branch("master", "origin/master")

    project(["remote", "add", "repo1", repo1.workdir])
    project(["fetch", "--all"])

    local_branches, remote_branches, tags = [
        *project.branches(project.BETA_BRANCHES),
        project(["tag", "-l"]).split(),
    ]

    repo = Repository(project.workdir)
    assert (local_branches, remote_branches, tags) \
           == scm.extract_beta_branches_and_release_tags(repo)

    assert local_branches == ["beta/0.0.1", "beta/0.0.4"]
    assert remote_branches == {
        "origin": ["beta/0.0.3", "beta/0.0.4"],
        "repo1": ["beta/0.0.2"],
    }
    assert tags == ["release/0.0.3", "release/0.0.4"]
