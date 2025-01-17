#!/usr/bin/python3

import os
import requests
import configbag
import click
from launchpadlib.launchpad import Launchpad
from lazr.restfulclient.errors import HTTPError
from configbag import get_tracks
from subprocess import check_call, CalledProcessError
from utils import upstream_release


gh_user = os.environ.get("GH_USER")
gh_token = os.environ.get("GH_TOKEN")


def is_latest(release):
    """Return true is the release passed is the latest stable one"""
    if release == "latest":
        return True

    latest_release_url = "https://dl.k8s.io/release/stable.txt"
    r = requests.get(latest_release_url)
    if r.status_code == 200:
        version = r.content.decode().strip()
        ersion = version[1:]
        ersion_nums = ersion.split(".")
        major_minor = "{}.{}".format(ersion_nums[0], ersion_nums[1])
        click.echo("Latest release is {} =?= {}".format(major_minor, release))
        return major_minor == release
    else:
        click.echo("Failed to get latest release info.")
        return False


def gh_branch_exists(branch):
    """Return true if the branch is already available on the repository"""
    cmd = "git ls-remote --exit-code --heads https://github.com/ubuntu/microk8s.git refs/heads/{}".format(
        branch
    ).split()
    try:
        check_call(cmd)
        click.echo("GH branch {} exists.".format(branch))
        return True
    except CalledProcessError:
        click.echo("GH branch does not {} exist.".format(branch))
        return False


def create_gh_branch(branch, gh_user, gh_token):
    """Create a branch on the repo using the credentials passed"""
    cmd = "rm -rf microk8s".split()
    check_call(cmd)
    cmd = "git clone https://github.com/ubuntu/microk8s".split()
    check_call(cmd)
    os.chdir("microk8s")
    cmd = "git config user.name cdkbot".split()
    check_call(cmd)
    cmd = "git config user.email cdkbot@gmail.com".split()
    check_call(cmd)
    cmd = "git checkout -b {}".format(branch).split()
    check_call(cmd)
    cmd = "sed -i s/KUBE_TRACK:-/KUBE_TRACK:-{}/g build-scripts/set-env-variables.sh".format(
        branch
    ).split()
    check_call(cmd)
    cmd = "sed -i s@UPGRADE_MICROK8S_FROM=latest/edge@UPGRADE_MICROK8S_FROM={}/edge@g .travis.yml".format(
        branch
    ).split()
    check_call(cmd)
    cmd = "git add .".split()
    check_call(cmd)
    cmd = "git commit -m".split()
    cmd.append("Creating branch {}".format(branch))
    check_call(cmd)
    cmd = "git push https://{}:{}@github.com/ubuntu/microk8s.git {}".format(
        gh_user, gh_token, branch
    ).split()
    check_call(cmd)


class Builder:
    """
    This class encapsulated all the functionality we need to manipulate the LP builders
    """

    def __init__(self, track, build_from_master=False):
        self.track = track
        self.is_latest = is_latest
        # the latest and the latest stable tracks (1.12 at the time of this writing)
        # build from the master head GH repo
        self.gh_branch = (
            "refs/heads/master" if build_from_master else "refs/heads/{}".format(track)
        )
        self.snap = None
        self.lp = None

    def exists(self):
        """Return True if the builder already exists"""
        try:
            if self._get_snap():
                return True
            else:
                return False
        except NameError as a:
            return False

    def create(self):
        """Create a new LP builder"""
        if self.track == "latest":
            snap_name = "microk8s"
        else:
            snap_name = "microk8s-{}".format(self.track)

        launchpad = self._get_lp()
        # get launchpad team data and ppa
        snappydev = launchpad.people[configbag.people_name]
        workingsnap = launchpad.snaps.getByName(name="microk8s", owner=snappydev)
        click.echo("Creating new LP builder for {}".format(self.gh_branch))
        launchpad.snaps.new(
            name=snap_name,
            owner=snappydev,
            distro_series=workingsnap.distro_series,
            git_repository=workingsnap.git_repository,
            git_path=self.gh_branch,
            store_upload=workingsnap.store_upload,
            store_name=workingsnap.store_name,
            store_series=workingsnap.store_series,
            store_channels="{}/edge".format(self.track),
            processors=[
                "/+processors/amd64",
                "/+processors/arm64",
                "/+processors/s390x",
            ],
            auto_build=workingsnap.auto_build,
            auto_build_archive=workingsnap.auto_build_archive,
            auto_build_pocket=workingsnap.auto_build_pocket,
        )

    def patch_latest(self):
        """Patch the git branch of the respective builder"""
        snap = self._get_snap()
        click.echo("Updating the LP builder of {}".format(self.gh_branch))
        snap.git_path = self.gh_branch
        snap.lp_save()

    def _get_lp(self):
        if not self.lp:
            # log in
            launchpad = Launchpad.login_with(
                "Launchpad Snap Build Trigger",
                "production",
                configbag.cachedir,
                credentials_file=configbag.creds,
                version="devel",
            )
            self.lp = launchpad

        return self.lp

    def _get_snap(self):
        if not self.snap:
            if self.track == "latest":
                snap_name = "microk8s"
            else:
                snap_name = "microk8s-{}".format(self.track)

            launchpad = self._get_lp()

            # get launchpad team data and ppa
            snappydev = launchpad.people[configbag.people_name]

            try:
                # get snap
                click.echo("Get snap {}".format(snap_name))
                microk8s = launchpad.snaps.getByName(name=snap_name, owner=snappydev)
                self.snap = microk8s
            except HTTPError as e:
                click.echo("Cannot get snap {}. ({})".format(snap_name, e.response))
                return None

        return self.snap


if __name__ == "__main__":
    click.echo("Validating GH branches and LP builders of microk8s")
    for track in get_tracks(all=True):
        click.echo("Examining track {}".format(track))
        upstream = upstream_release(track)
        if not upstream:
            click.echo("Nothing upstream for this track. Skipping.")
            continue

        # Take care of the GH branches
        if not is_latest(track) and not gh_branch_exists(track):
            click.echo("Creating a branch for {}".format(track))
            create_gh_branch(track, gh_user, gh_token)
            click.echo("Creating GH branch from master.")
            # it will take at most 5 hours for LP to get the branch so
            # trying to create the LP builders now will fail.
            # We continue to the next track and we will create the LP builders
            # in the next execution of this script.
            continue

        # Take care of the LP builders
        build_from_master = is_latest(track) and not gh_branch_exists(track)
        builder = Builder(track, build_from_master)
        if not builder.exists():
            builder.create()
        else:
            builder.patch_latest()
