import os
import subprocess
from pathlib import Path

base_folder = Path(__file__).resolve().parent

def get_git_tag():
    git_tag = os.getenv("OPENVIC_TAG", "<tag missing>")
    if os.path.exists(".git"):
        try:
            result = subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"], encoding="utf-8").strip()
            if result != "":
                git_tag = result
        except (subprocess.CalledProcessError, OSError):
            # `git` not found in PATH.
            pass
    
    return git_tag

def get_git_release():
    git_release = os.getenv("OPENVIC_RELEASE", "<release missing>")
    if os.path.exists(".git"):
        try:
            result = subprocess.check_output(["gh", "release", "list", "--json", "name", "-q", ".[0] | .name"], encoding="utf-8").strip()
            if result != "":
                git_release = result
        except (subprocess.CalledProcessError, OSError):
            # `gh` not found in PATH.
            git_tag = get_git_tag()
            if git_tag != "<tag missing>":
                git_release = git_tag
    
    return git_release

def get_git_hash():
    # Parse Git hash if we're in a Git repo.
    git_hash = "0000000000000000000000000000000000000000"
    git_folder = ".git"

    if os.path.isfile(".git"):
        with open(".git", "r", encoding="utf-8") as file:
            module_folder = file.readline().strip()
        if module_folder.startswith("gitdir: "):
            git_folder = module_folder[8:]

    if os.path.isfile(os.path.join(git_folder, "HEAD")):
        with open(os.path.join(git_folder, "HEAD"), "r", encoding="utf8") as file:
            head = file.readline().strip()
        if head.startswith("ref: "):
            ref = head[5:]
            # If this directory is a Git worktree instead of a root clone.
            parts = git_folder.split("/")
            if len(parts) > 2 and parts[-2] == "worktrees":
                git_folder = "/".join(parts[0:-2])
            head = os.path.join(git_folder, ref)
            packedrefs = os.path.join(git_folder, "packed-refs")
            if os.path.isfile(head):
                with open(head, "r", encoding="utf-8") as file:
                    git_hash = file.readline().strip()
            elif os.path.isfile(packedrefs):
                # Git may pack refs into a single file. This code searches .git/packed-refs file for the current ref's hash.
                # https://mirrors.edge.kernel.org/pub/software/scm/git/docs/git-pack-refs.html
                for line in open(packedrefs, "r", encoding="utf-8").read().splitlines():
                    if line.startswith("#"):
                        continue
                    (line_hash, line_ref) = line.split(" ")
                    if ref == line_ref:
                        git_hash = line_hash
                        break
        else:
            git_hash = head

    # Get the UNIX timestamp of the build commit.
    git_timestamp = 0
    if os.path.exists(".git"):
        try:
            git_timestamp = subprocess.check_output(
                ["git", "log", "-1", "--pretty=format:%ct", "--no-show-signature", git_hash], encoding="utf-8"
            )
        except (subprocess.CalledProcessError, OSError):
            # `git` not found in PATH.
            pass

    return {
        "git_hash": git_hash,
        "git_timestamp": git_timestamp,
    }

def get_git_info():
    return {**get_git_hash(), "git_tag": get_git_tag(), "git_release": get_git_release() }