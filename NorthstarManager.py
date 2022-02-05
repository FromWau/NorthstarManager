import configparser
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import requests
from github import Github
from github.GitRelease import GitRelease
from github.GithubException import RateLimitExceededException
from tqdm import tqdm

config = configparser.ConfigParser()
g = Github()

print(f"[{time.strftime('%H:%M:%S')}] [info]    Reading config from 'updater_config.ini'...")
config.read("updater_config.ini")
if len(config.sections()) == 0:
    print(f"[{time.strftime('%H:%M:%S')}] [warning] 'updater_config.ini' is empty or does not exist")
    print(f"[{time.strftime('%H:%M:%S')}] [info]    Using default config instead")
    config["Northstar"] = {
        "repository": "R2Northstar/Northstar",
        "last_update": "0001-01-01T00:00:00",
        "ignore_prerelease": "true",
        "file": "NorthstarLauncher.exe",
        "install_dir": ".",
        "exclude_files": "ns_startup_args.txt|ns_startup_args_dedi.txt",
    }
    config["NorthstarManager"] = {
        "repository": "FromWau/NorthstarManager",
        "last_update": "0001-01-01T00:00:00",
        "ignore_prerelease": "true",
        "file": "NorthstarManager.exe",
        "install_dir": ".",
        "exclude_files": "",
    }
    config["ExampleMod"] = {
        "repository": "example/example-mod",
        "last_update": "0001-01-01T00:00:00",
    }
    config["Launcher"] = {
        "filename": "NorthstarLauncher.exe",
        "arguments": "-multiple",
    }
    config["SkinTool"] = {
        "repository": "zxcPandora/Titanfall2-SkinTool",
        "last_update": "0001-01-01T00:00:00",
        "ignore_prerelease": "true",
        "install_dir": "."
    }


def download(url, download_file):
    with requests.get(url, stream=True) as response:
        total = int(response.headers.get("content-length", 0))
        block_size = 1024
        with tqdm(
                total=total, unit_scale=True, unit_divisor=block_size, unit="B"
        ) as progress:
            for data in response.iter_content(block_size):
                progress.update(len(data))
                download_file.write(data)


class NoValidRelease(Exception):
    pass


class NoValidAsset(Exception):
    pass


class FileNotInZip(Exception):
    pass


update_everything = False
try:
    i = sys.argv.index("--update-everything")
    sys.argv.pop(i)
    update_everything = True
except ValueError:
    pass


class Updater:
    def __init__(self, blockname):
        self.blockname = blockname
        self.repository = config.get(blockname, "repository")
        self._file = config.get(self.blockname, "file", fallback="mod.json")
        self.repo = g.get_repo(self.repository)
        self.ignore_prerelease = config.getboolean(
            blockname, "ignore_prerelease", fallback=True
        )
        self.install_dir = Path(
            config.get(blockname, "install_dir", fallback="./R2Northstar/mods")
        )
        self.file = (self.install_dir / self._file).resolve()
        self.exclude_files = config \
            .get(blockname, "exclude_files", fallback="") \
            .split("|")

    @property
    def last_update(self):
        return datetime.fromisoformat(
            config.get(self.blockname, "last_update", fallback=datetime.min.isoformat())
        )

    @last_update.setter
    def last_update(self, value: datetime):
        config.set(self.blockname, "last_update", value.isoformat())

    def release(self):
        releases = self.repo.get_releases()
        for release in releases:
            if release.prerelease and self.ignore_prerelease:
                continue
            if update_everything:
                return release
            if release.published_at > self.last_update:
                return release
            if self._file != "mod.json":
                if not self.file.exists() or self._file != "NorthstarLauncher.exe":
                    return release
            break  # stop search wenn aktuellere Version vorhanden ist
        raise NoValidRelease("Found No new releases")

    def asset(self, release: GitRelease) -> str:
        print(f"[{time.strftime('%H:%M:%S')}] [info]    Updating to   new release  for {self.blockname} published Version {release.tag_name}")
        assets = release.get_assets()

        if assets.totalCount == 0:  # if no application release exists try download source direct.
            return release.zipball_url
        else:
            for asset in assets:
                if asset.content_type in (
                        "application/zip",
                        "application/x-zip-compressed",
                ):
                    return asset.browser_download_url
            raise NoValidAsset("No valid asset was found in release")

    def _mod_json_extractor(self, zip_: zipfile.ZipFile):
        parts = None
        found = None
        for fileinfo in zip_.infolist():
            fp = Path(fileinfo.filename)
            if fp.name == self._file:
                parts = fp.parts[:-2]
                found = fp
                break
        if parts:
            for fileinfo in zip_.infolist():
                fp = Path(fileinfo.filename)
                strip = len(parts)
                if fp.parts[:strip] == parts:
                    new_fp = Path(*fp.parts[strip:])
                    fileinfo.filename = str(new_fp) + ("/" if fileinfo.filename.endswith("/") else "")
                    zip_.extract(fileinfo, self.install_dir)
        elif found:
            for fileinfo in zip_.infolist():
                if zip_.filename:
                    Path(Path(zip_.filename).stem) / fileinfo.filename
                    zip_.extract(fileinfo, self.install_dir)
        else:
            raise FileNotInZip(f"mod.json not found in the selected release zip.")

    def _file_extractor(self, zip_: zipfile.ZipFile):
        namelist = zip_.namelist()
        if self._file in namelist or self._file.strip("/") + "/mod.json" in namelist:
            for file_ in namelist:
                if file_ not in self.exclude_files:
                    zip_.extract(file_, self.install_dir)
                else:
                    if not Path(file_).exists():  # check for first time install of excluded files
                        zip_.extract(file_, self.install_dir)
        else:
            for zip_info in zip_.infolist():
                print(zip_info.filename)
            raise FileNotInZip(f"{self._file} not found in the selected release zip.")

    def extract(self, zip_: zipfile.ZipFile):
        if self._file != "mod.json":
            self._file_extractor(zip_)
        else:
            self._mod_json_extractor(zip_)

    def run(self):
        try:
            release = self.release()
            url = self.asset(release)
        except NoValidRelease:
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Found no      new releases for {self.blockname}")
            return
        except NoValidAsset:
            print(f"[{time.strftime('%H:%M:%S')}] [warning] Possibly faulty   release  for {self.blockname} published Version {release.tag_name} has no vali assets")
            return
        with tempfile.NamedTemporaryFile() as download_file:
            download(url, download_file)
            release_zip = zipfile.ZipFile(download_file)
            self.extract(release_zip)
            self.last_update = release.published_at
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Updated successfully           {self.blockname} to        Version {release.tag_name}")


class SelfUpdater(Updater):
    def release(self):
        releases = self.repo.get_releases()
        for release in releases:
            if release.prerelease and self.ignore_prerelease:
                continue
            if update_everything or \
                    not self.file.exists() or \
                    release.published_at > self.last_update or \
                    datetime.fromtimestamp(self.file.stat().st_mtime) < release.published_at - timedelta(hours=1):
                try:  # if asset not available contine search
                    return release, self.asset(release)
                except NoValidAsset:
                    continue

        raise NoValidRelease("No new release found")

    def asset(self, release: GitRelease):
        print(f"[{time.strftime('%H:%M:%S')}] [info]    Updating to   new release  for {self.blockname} published Version {release.tag_name}")
        assets = release.get_assets()
        for asset in assets:
            if asset.content_type in "application/octet-stream":
                return asset
        raise NoValidAsset("No valid asset was found in release")

    def run(self):
        try:
            release, asset = self.release()
        except NoValidRelease:
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Found no      new releases for {self.blockname}")
            return
        except NoValidAsset:
            print(f"[{time.strftime('%H:%M:%S')}] [warning] Possibly faulty   release  for {self.blockname} published Version {release.tag_name} has no vali assets")
            return
        with tempfile.NamedTemporaryFile(delete=False) as download_file:
            download(asset.browser_download_url, download_file)

        newfile: Path = self.file.with_suffix(".new")
        shutil.move(download_file.name, newfile)
        script = f"timeout 20 && del {self.file} && move {newfile} {self.file} && del {newfile}"
        subprocess.Popen(["cmd", "/c", script])
        self.last_update = release.published_at
        print(f"[{time.strftime('%H:%M:%S')}] [info]    Updated successfully           {self.blockname} to        Version {release.tag_name}")


def main():

    while not updater():  # restart for github rate error
        print(f"[{time.strftime('%H:%M:%S')}] [info]    Waiting and restarting Updater in 60s...")
        time.sleep(60)

    launcher()


def updater() -> bool:
    for section in config.sections():
        try:
            if section not in ("Launcher", "ExampleMod"):
                print(f"[{time.strftime('%H:%M:%S')}] [info]    Searching for new Releases for {section}...")
                if section == "NorthstarManager":
                    u = SelfUpdater(section)
                    u.run()
                else:
                    u = Updater(section)
                    u.run()
        except RateLimitExceededException:
            print(f"[{time.strftime('%H:%M:%S')}] [warning] GitHub rate exceeded for {section}.")
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Available requests left {g.rate_limiting[0]}/{g.rate_limiting[1]}.")
            inp = input("Launch Northstar without checking for updates? (y/n) ")
            if inp != "n":
                break
            return False
        except FileNotInZip:
            print(f"[{time.strftime('%H:%M:%S')}] [warning] Zip file for {section} doesn't contain expected files.")
    return True


def launcher():
    try:
        action = "./__Installer/Origin/redist/internal/OriginThinSetup.exe"
        print(f"[{time.strftime('%H:%M:%S')}] [info]    Launching OriginThinClient")
        subprocess.run([action], cwd=str(Path.cwd()))
        print(f"[{time.strftime('%H:%M:%S')}] [info]    Launching {config.get('Launcher', 'filename')} "
              f"{config.get('Launcher', 'arguments')} "
              f"{''.join(sys.argv[1:])} in 10sec...")
        time.sleep(10)
        action = config.get('Launcher', 'filename')
        subprocess.run(
            [action]
            + config.get("Launcher", "arguments").split(" ")
            + sys.argv[1:],
            cwd=str(Path.cwd())
        )
    except FileNotFoundError:
        print(f"[{time.strftime('%H:%M:%S')}] [warning] Could not run {action}")


main()
with open("updater_config.ini", "w+") as f:
    config.write(f)
