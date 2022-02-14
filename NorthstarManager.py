import json
import pprint
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import confuse
import requests
import yaml
from github import Github
from github.GitRelease import GitRelease
from github.GithubException import RateLimitExceededException, BadCredentialsException
from tqdm import tqdm

args = ""
showhelp = False
try:
    i = sys.argv.index("-help")
    args += " " + sys.argv.pop(i)
    showhelp = True
except ValueError:
    pass

updateAll = False
try:
    i = sys.argv.index("-updateAll")
    args += " " + sys.argv.pop(i)
    updateAll = True
except ValueError:
    pass

updateAllIgnoreManager = False
try:
    i = sys.argv.index("-updateAllIgnoreManager")
    args += " " + sys.argv.pop(i)
    updateAllIgnoreManager = True
except ValueError:
    pass

onlyUpdate = False
try:
    i = sys.argv.index("-onlyUpdate")
    args += " " + sys.argv.pop(i)
    onlyUpdate = True
except ValueError:
    pass

onlyLaunch = False
try:
    i = sys.argv.index("-onlyLaunch")
    args += " " + sys.argv.pop(i)
    onlyLaunch = True
except ValueError:
    pass

asdedicated = False
try:
    i = sys.argv.index("-dedicated")
    args += " " + sys.argv.pop(i)
    onlyLaunch = True
except ValueError:
    pass

createServer = False
createServerPath = ""
try:
    i = sys.argv.index("-createServer")
    sp = sys.argv[i + 1:i + 2][0]
    if Path(sp).exists():
        args += " " + sys.argv.pop(i)
        createServerPath = sys.argv.pop(sys.argv.index(sp))
        args += " " + createServerPath
        createServer = True
    else:
        print(
            f"[{time.strftime('%H:%M:%S')}] [warning] Arg -createServer given file location does not exist{createServerPath}")
except IndexError:
    print(f"[{time.strftime('%H:%M:%S')}] [warning] Arg -createServer is missing the location for the server")
except ValueError:
    pass

print(
    f"[{time.strftime('%H:%M:%S')}] [info]    Launched NorthstarManager with {'no args' if len(args) == 0 else 'arguments:' + args}")
config = confuse.Configuration("NorthstarManager", __name__)


def loaddefaultconf():
    print(f"[{time.strftime('%H:%M:%S')}] [info]    Using default config instead")
    config.set({
        'GLOBAL': {
            'github_token': '',
        },
        'Launcher': {
            'argumnets': '',
            'filename': 'NorthstarLauncher.exe',
        },
        'Manager': {
            'file': 'NorthstarManager.exe',
            'ignore_prerelease': True,
            'install_dir': '.',
            'last_update': '0001-01-01T00:00:00',
            'repository': 'FromWau/NorthstarManager',
        },
        'Mods': {
            'Northstar': {
                'exclude_files': ['ns_startup_args.txt', 'ns_startup_args_dedi.txt'],
                'file': 'NorthstarLauncher.exe',
                'ignore_prerelease': True,
                'ignore_updates': False,
                'install_dir': '.',
                'last_update': '0001-01-01T00:00:00',
                'repository': 'R2Northstar/Northstar',
            }
        },

    })


print(f"[{time.strftime('%H:%M:%S')}] [info]    Reading config from 'manager_config.yaml'...")
if not Path("manager_config.yaml").exists():
    print(f"[{time.strftime('%H:%M:%S')}] [warning] 'manager_config.yaml' does not exist")
    loaddefaultconf()
    with open("manager_config.yaml", "w+") as f:
        f.write(config.dump())

config.set_file("manager_config.yaml")
config.read()
try:
    for i in ["Manager", "Launcher", "Mods"]:
        config.keys().remove(i)
except ValueError:
    print(f"[{time.strftime('%H:%M:%S')}] [warning] 'manager_config.yaml' is empty or invalid")
    loaddefaultconf()

token = config['GLOBAL']['github_token'].get(confuse.Optional(str, default=""))
try:
    if len(token) == 0:
        g = Github()
        print(
            f"[{time.strftime('%H:%M:%S')}] [info]    No configurated github_token, running with a rate limit of {g.rate_limiting[0]}/{g.rate_limiting[1]}")
    else:
        g = Github(token)
        print(
            f"[{time.strftime('%H:%M:%S')}] [info]    Using configurated github_token, running with a rate limit of {g.rate_limiting[0]}/{g.rate_limiting[1]}")
except BadCredentialsException:
    print(
        f"[{time.strftime('%H:%M:%S')}] [warning] GitHub Token invalid or maybe expired. Check on https://github.com/settings/tokens")
    token = ""
    g = Github()
    print(
        f"[{time.strftime('%H:%M:%S')}] [info]    Using no GitHub Token, running with a rate limit of {g.rate_limiting[0]}/{g.rate_limiting[1]}")

script_queue = []


def printhelp():
    print(f"[{time.strftime('%H:%M:%S')}] [info]    Printing help")
    print(
        "Launch arguments can be set in the 'config_updater.ini'. List of launch arguments:\n"
        "-help ................. prints this help\n"
        "-updateAll ............ updates all repos defined in the 'config_updater.ini' to the latest release regardless of maybe being the latest release, ignoring flags: 'ignore_updates'\n"
        "-onlyUpdate ........... only runs the updater without launching the defined launcher in the 'config_updater.ini'\n"
        "-onlyLaunch ........... only launches the defined launcher in the 'config_updater.ini', without updating\n"
        "-dedicated ............ runs the laucnher as dedicated server\n"
        "\n"
        "Northstar Client/ vanilla TF2 args should be put into the ns_startup_args.txt or ns_startup_args_dedi.txt for dedicated servers\n"
        "All Northstar launch arguments can be found at the official wiki: https://r2northstar.gitbook.io/r2northstar-wiki/using-northstar/launch-arguments \n"
        "All vanilla TF2 launch arguments can be found at the source wiki: https://developer.valvesoftware.com/wiki/Command_Line_Options#Command-line_parameters \n"
    )


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


def createserver(serverpath):
    current_dir = Path.cwd().resolve()
    pass_args = " -updateAll -onlyUpdate"

    script_queue.append(
        f"echo [{time.strftime('%H:%M:%S')}] [info]    Started setup for dedicated Northstar server at {serverpath} && "
        f"echo [{time.strftime('%H:%M:%S')}] [info]    Copying TF2 files to new server location && "
        f'xcopy "{current_dir}/__Installer" "{serverpath}/__Installer/" /s /e /q /I && '
        f'xcopy "{current_dir}/bin" "{serverpath}/bin/" /s /e /q /I && '
        f'xcopy "{current_dir}/Core" "{serverpath}/Core/" /s /e /q /I && '
        f'xcopy "{current_dir}/platform" "{serverpath}/platform/" /s /e /q /I && '
        f'xcopy "{current_dir}/Support" "{serverpath}/Support/" /s /e /q /I && '
        f'xcopy "{current_dir}\\build.txt" "{serverpath}" /q && '
        f'xcopy "{current_dir}\\gameversion.txt" "{serverpath}" /q && '
        f'xcopy "{current_dir}\\server.dll" "{serverpath}" /q && '
        f'xcopy "{current_dir}\\Titanfall2.exe" "{serverpath}" /q && '
        f'xcopy "{current_dir}\\Titanfall2_trial.exe" "{serverpath}" /q && '
        f"echo [{time.strftime('%H:%M:%S')}] [info]    Creating a junction for vpk and r2 && "
        f'mklink /j "{serverpath}/vpk" "{current_dir}/vpk" && '
        f'mklink /j "{serverpath}/r2" "{current_dir}/r2" && '
        f"echo [{time.strftime('%H:%M:%S')}] [info]    Copying NorthstarManager to new server location && "
        f'xcopy "{current_dir}\\NorthstarManager.exe" "{serverpath}" /q  && '
        f"echo [{time.strftime('%H:%M:%S')}] [info]    Launch initial setup for NorthstarManager.exe{pass_args}  && "
        f'cd /d "{serverpath}" && '
        f'"NorthstarManager.exe"{pass_args} && '
        f"echo [{time.strftime('%H:%M:%S')}] [info]    Successfully setup dedicated Northstar server. Run dedicated server with: NorthstarManager.exe -dedicated"
    )
    raise HaltandRunScripts("restart manager")


def install_tf2(installpath):
    originpath = Path.cwd()
    scripts = [
        f'xcopy "{originpath}/__Installer" "{installpath}/__Installer/" /s /e /q /I && '
        f'xcopy "{originpath}/bin" "{installpath}/bin/" /s /e /q /I && '
        f'xcopy "{originpath}/Core" "{installpath}/Core/" /s /e /q /I && '
        f'xcopy "{originpath}/platform" "{installpath}/platform/" /s /e /q /I && '
        f'xcopy "{originpath}/Support" "{installpath}/Support/" /s /e /q /I && '
        f'xcopy "{originpath}\\build.txt" "{installpath}" /q && '
        f'xcopy "{originpath}\\gameversion.txt" "{installpath}" /q && '
        f'xcopy "{originpath}\\server.dll" "{installpath}" /q && '
        f'xcopy "{originpath}\\Titanfall2.exe" "{installpath}" /q && '
        f'xcopy "{originpath}\\Titanfall2_trial.exe" "{installpath}" /q && '
        f"echo [{time.strftime('%H:%M:%S')}] [info]    Creating a junction for vpk and r2 && "
        f'mklink /j "{installpath}/vpk" "{originpath}/vpk" && '
        f'mklink /j "{installpath}/r2" "{originpath}/r2"'
    ]
    print(f"[{time.strftime('%H:%M:%S')}] [info]    Copying TF2 files to {installpath.absolute()}")
    for script in scripts:
        subprocess.Popen(script, cwd=str(Path.cwd()), shell=True).wait()
    print(f"[{time.strftime('%H:%M:%S')}] [info]    Successfully setup dedicated Northstar server. Run dedicated server with: 'cd /d {installpath.absolute()}; ./NorthstarManager.exe -dedicated'")


class NoValidRelease(Exception):
    pass


class NoValidAsset(Exception):
    pass


class FileNotInZip(Exception):
    pass


class HaltandRunScripts(Exception):
    pass


class ManagerUpdater:
    def __init__(self, path):
        yamlpath = config
        for index in path:
            yamlpath = yamlpath[index]
        self.yamlpath = yamlpath
        self.blockname = path[-1]
        self.repository = yamlpath["repository"].get()
        self.repo = g.get_repo(self.repository)
        self.ignore_updates = yamlpath["ignore_updates"].get(confuse.Optional(bool, default=False))
        if self.ignore_updates:
            print(
                f"[{time.strftime('%H:%M:%S')}] [info]    Search stopped for new releases  for {self.blockname}, ignore_updates flag is set")
            return
        self.ignore_prerelease = yamlpath["ignore_prerelease"].get(confuse.Optional(bool, default=True))
        self.install_dir = Path(yamlpath["install_dir"].get(confuse.Optional(str, default=".")))
        self._file = yamlpath["file"].get(confuse.Optional(str, default="NorthstarController.exe"))
        self.file = (self.install_dir / self._file).resolve()

    @property
    def last_update(self):
        return datetime.fromisoformat(config[self.blockname]["last_update"])  # fallback=datetime.min.isoformat()

    @last_update.setter
    def last_update(self, value: datetime):
        config.get()[self.blockname]["last_update"] = value.isoformat()

    def release(self):
        releases = self.repo.get_releases()
        for release in releases:
            if release.prerelease and self.ignore_prerelease:
                continue
            if updateAll or \
                    not self.file.exists() or \
                    release.published_at > self.last_update or \
                    datetime.fromtimestamp(self.file.stat().st_mtime) < release.published_at - timedelta(minutes=10):
                try:  # if asset not available contine search
                    return release, self.asset(release)
                except NoValidAsset:
                    continue
        raise NoValidRelease("No new release found")

    def asset(self, release: GitRelease):
        print(
            f"[{time.strftime('%H:%M:%S')}] [info]    Updating to        new release   for {self.blockname} published Version {release.tag_name}")
        assets = release.get_assets()
        for asset in assets:
            if asset.content_type in "application/octet-stream":
                return asset
        raise NoValidAsset("No valid asset was found in release")

    def run(self):
        if self.ignore_updates:
            return
        try:
            release, asset = self.release()
        except NoValidRelease:
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Latest Version already installed for {self.blockname}")
            return
        except NoValidAsset:
            print(
                f"[{time.strftime('%H:%M:%S')}] [warning] Possibly faulty        release   for {self.blockname} published Version {release.tag_name} has no valit assets")
            return
        with tempfile.NamedTemporaryFile(delete=False) as download_file:
            download(asset.browser_download_url, download_file)

        newfile: Path = self.file.with_suffix(".new")
        shutil.move(download_file.name, newfile)
        self.last_update = release.published_at
        print(
            f"[{time.strftime('%H:%M:%S')}] [info]    Stopped Updater and rerun new Version of {self.blockname} after install")

        pass_args = " -onlyUpdate" if onlyUpdate else ""
        pass_args += " -dedicated" if asdedicated else ""
        pass_args += " -updateAllIgnoreManager" if updateAll else ""

        script_queue.append(
            f"echo [{time.strftime('%H:%M:%S')}] [info]    Running self-replacer            for {self.blockname} && "
            f"timeout /t 5 && "
            f'del "{self.file}" && '
            f'move "{newfile}" "{self.file}" && '
            f"echo [{time.strftime('%H:%M:%S')}] [info]    Installed successfully update    for {self.blockname} && "
            f"echo [{time.strftime('%H:%M:%S')}] [info]    Launching latest install         of  {self.file.name}{pass_args} && "
            f'"{self.file.name}"{pass_args}'
        )
        raise HaltandRunScripts("restart manager")


class ModUpdater:
    def __init__(self, path):
        yamlpath = config
        for index in path:
            yamlpath = yamlpath[index]
        self.yamlpath = yamlpath
        self.blockname = path[-1]
        self.repository = self.yamlpath["repository"].get()
        self.repo = g.get_repo(self.repository)
        self.ignore_updates = self.yamlpath["ignore_updates"].get(confuse.Optional(bool, default=False))
        if self.ignore_updates:
            print(
                f"[{time.strftime('%H:%M:%S')}] [info]    Search stopped for new releases  for {self.blockname}, ignore_updates flag is set")
            return
        self.ignore_prerelease = (
                self.yamlpath["ignore_prerelease"].get(confuse.Optional(bool, default=True)) == 'True')
        self.install_dir = Path(self.yamlpath["install_dir"].get(confuse.Optional(str, default="./R2Northstar/mods")))
        self._file = self.yamlpath["file"].get(confuse.Optional(str, default="mod.json"))
        self.file = (self.install_dir / self._file).resolve()
        self.exclude_files = self.yamlpath["exclude_files"].get(confuse.Optional(list, default=[]))

    @property
    def last_update(self):
        return datetime.fromisoformat(
            self.yamlpath["last_update"].get(confuse.Optional(datetime, default=datetime.min.isoformat())))

    @last_update.setter
    def last_update(self, value: datetime):
        self.yamlpath.get()["last_update"] = value.isoformat()

    def release(self):
        releases = self.repo.get_releases()
        for release in releases:
            if release.prerelease and self.ignore_prerelease:
                continue
            if updateAll or updateAllIgnoreManager or \
                    release.published_at > self.last_update:
                return release
            if self._file != "mod.json":
                if not self.file.exists() or self._file != "NorthstarLauncher.exe":
                    return release
            break  # stop search wenn aktuellere Version vorhanden ist
        raise NoValidRelease("Found No new releases")

    def asset(self, release: GitRelease) -> str:
        print(
            f"[{time.strftime('%H:%M:%S')}] [info]    Updating to        new release   for {self.blockname} published Version {release.tag_name}")
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
                    if not Path(file_).exists():  # check for first time installation of excluded files
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
        if self.ignore_updates:
            return
        try:
            release = self.release()
            url = self.asset(release)
        except NoValidRelease:
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Latest Version already installed for {self.blockname}")
            return
        except NoValidAsset:
            print(
                f"[{time.strftime('%H:%M:%S')}] [warning] Possibly faulty        release   for {self.blockname} published Version {release.tag_name} has no valit assets")
            return
        with tempfile.NamedTemporaryFile() as download_file:
            download(url, download_file)
            release_zip = zipfile.ZipFile(download_file)
            self.extract(release_zip)
            self.last_update = release.published_at
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Installed successfully update    for {self.blockname}")


def main():
    try:
        # if createServer:
        # createserver(serverpath=createServerPath)
        # %TODO configuration
        if showhelp:
            printhelp()
            return

        if onlyLaunch:
            launcher()
            return

        while not updater():  # restart when encountering a GitHub rate error
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Waiting and restarting Updater in 60s...")
            time.sleep(60)

        if not onlyUpdate:
            launcher()
    except HaltandRunScripts:
        for script in script_queue:
            subprocess.Popen(script, cwd=str(Path.cwd()), shell=True)


def updater() -> bool:
    yamlpath = []
    for section in config.keys():
        try:
            # match case not usable due to nuitka
            # match section:
            #     case ("GLOBAL", "Launcher"):
            #         continue
            #     case "Manager":
            #         if updateAllIgnoreManager:
            #             continue
            #         yamlpath = [section]
            #         print(f"[{time.strftime('%H:%M:%S')}] [info]    Searching for      new releases  for {'/'.join(yamlpath)}...")
            #         ManagerUpdater(section).run()
            #     case "Mods":
            #         for mod in config[section]:
            #             yamlpath = [section, mod]
            #             print(f"[{time.strftime('%H:%M:%S')}] [info]    Searching for      new releases  for {'/'.join(yamlpath)}...")
            #             ModUpdater(yamlpath).run()
            #     case "Servers":
            #         for server in config[section]:
            #             for mod in config[section][server]["Mods"]:
            #                 yamlpath = [section, server, "Mods", mod]
            #                 print(f"[{time.strftime('%H:%M:%S')}] [info]    Searching for      new releases  for {'/'.join(yamlpath)}...")
            #                 ModUpdater(yamlpath).run()
            #     case _ as yamlsection:
            #         print(f"[{time.strftime('%H:%M:%S')}] [warning] Yaml section {yamlsection}")

            if section in ("GLOBAL", "Launcher"):
                continue
            if section == "Manager" and not updateAllIgnoreManager:
                yamlpath = [section]
                print(f"[{time.strftime('%H:%M:%S')}] [info]    Searching for      new releases  for {'/'.join(yamlpath)}...")
                ManagerUpdater(yamlpath).run()
            if section == "Mods":
                for mod in config[section]:
                    yamlpath = [section, mod]
                    print(
                        f"[{time.strftime('%H:%M:%S')}] [info]    Searching for      new releases  for {'/'.join(yamlpath)}...")
                    ModUpdater(yamlpath).run()
            if section == "Servers":
                for server in config[section]:
                    for mod in config[section][server]["Mods"]:
                        yamlpath = [section, server, "Mods", mod]
                        print(f"[{time.strftime('%H:%M:%S')}] [info]    Searching for      new releases  for {'/'.join(yamlpath)}...")
                        ModUpdater(yamlpath).run()
                    # check if titanfall2.exe exists in server dir
                    server_path = Path(config[section][server]["dir"].get())
                    if not server_path.joinpath("Titanfall2.exe").exists():
                        install_tf2(server_path)

        except RateLimitExceededException:
            print(f"[{time.strftime('%H:%M:%S')}] [warning] GitHub rate exceeded for {'/'.join(yamlpath)}")
            print(
                f"[{time.strftime('%H:%M:%S')}] [info]    Available requests left {g.rate_limiting[0]}/{g.rate_limiting[1]}")
            if "y" != input("Wait and try update again in 60sec? (y/n) "):
                break
            return False
        except FileNotInZip:
            print(
                f"[{time.strftime('%H:%M:%S')}] [warning] Zip file for {'/'.join(yamlpath)} doesn't contain expected files")
    print(f"[{time.strftime('%H:%M:%S')}] [info]    Successfully checkt all mods")
    return True


def launcher():
    script = '"C:/Program Files (x86)/Origin/Origin.exe"'
    try:
        print(f"[{time.strftime('%H:%M:%S')}] [info]    Launching Origin and waiting 10sec...")
        subprocess.Popen(script, cwd=str(Path.cwd()))
        time.sleep(10)
        print(f"[{time.strftime('%H:%M:%S')}] [info]    Launched  Origin succesfull")

        script = [config['Launcher']['filename'].get()] + config['Launcher']['argumnets'].get().split(" ") + sys.argv[
                                                                                                             1:]
        print(f"[{time.strftime('%H:%M:%S')}] [info]    Launching {' '.join(script)}")
        subprocess.Popen(script, cwd=str(Path.cwd()))

        # taskkill /IM "origin.exe" /F
        # wait for Launcher to finish
    except FileNotFoundError:
        print(f"[{time.strftime('%H:%M:%S')}] [warning] Could not run {script}")


main()
with open("manager_config.yaml", "w+") as f:
    yaml.dump(json.loads(json.dumps(config.get())), f, allow_unicode=True)
