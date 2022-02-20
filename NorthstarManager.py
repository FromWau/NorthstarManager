import confuse
import ruamel.yaml
import psutil
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
from github.GithubException import RateLimitExceededException, BadCredentialsException, UnknownObjectException
from tqdm import tqdm

args = ""
showhelp = False  # print help and quit
try:
    i = sys.argv.index("-help")
    args += " " + sys.argv.pop(i)
    showhelp = True
except ValueError:
    pass

updateAll = False  # Force updates manager then relaunches manager with args -updateAllIgnoreManager
try:
    i = sys.argv.index("-updateAll")
    args += " " + sys.argv.pop(i)
    updateAll = True
except ValueError:
    pass

updateAllIgnoreManager = False  # everything in yaml configurated will get force updated
try:
    i = sys.argv.index("-updateAllIgnoreManager")
    args += " " + sys.argv.pop(i)
    updateAllIgnoreManager = True
except ValueError:
    pass

updateServers = False  # Force updates servers, ignoring enabled flags
try:
    i = sys.argv.index("-updateServers")
    args += " " + sys.argv.pop(i)
    updateServers = True
except ValueError:
    pass

updateClient = False  # Force updates client and all the mods of the client, ignoring enabled flags
try:
    i = sys.argv.index("-updateClient")
    args += " " + sys.argv.pop(i)
    updateClient = True
except ValueError:
    pass

onlyCheckAll = False  # runs the check for updates on the client and servers
try:
    i = sys.argv.index("-onlyCheckAll")
    args += " " + sys.argv.pop(i)
    onlyCheckAll = True
except ValueError:
    pass

onlyCheckServers = False  # only runs the check for updates on the servers
try:
    i = sys.argv.index("-onlyCheckServers")
    args += " " + sys.argv.pop(i)
    onlyCheckServers = True
except ValueError:
    pass

onlyCheckClient = False  # only runs the check for updates on the client
try:
    i = sys.argv.index("-onlyCheckClient")
    args += " " + sys.argv.pop(i)
    onlyCheckClient = True
except ValueError:
    pass

onlyLaunch = False  # no updates and runs launcher
try:
    i = sys.argv.index("-onlyLaunch")
    args += " " + sys.argv.pop(i)
    onlyLaunch = True
except ValueError:
    pass

print(f"[{time.strftime('%H:%M:%S')}] [info]    Launched NorthstarManager with {'no args' if len(args) == 0 else 'arguments:' + args}")

yaml = ruamel.yaml.YAML()
yaml.indent(mapping=4, sequence=2, offset=0)
global conf_comments

print(f"[{time.strftime('%H:%M:%S')}] [info]    Reading config from 'manager_config.yaml'...")
if not Path("manager_config.yaml").exists():
    print(f"[{time.strftime('%H:%M:%S')}] [warning] 'manager_config.yaml' does not exist")
    print(f"[{time.strftime('%H:%M:%S')}] [info]    Using default config instead")
    default_conf = """\
# This is the default config
# ==========================  
Global:
    # set github token here
    github_token:   

Launcher:
    filename: NorthstarLauncher.exe
    argumnets:

Manager:
    file: NorthstarManager.exe
    install_dir: .
    last_update: '0001-01-01T00:00:00'
    repository: FromWau/NorthstarManager

Mods:
    Northstar:
        exclude_files:
            - ns_startup_args.txt
            - ns_startup_args_dedi.txt
        file: NorthstarLauncher.exe
        ignore_prerelease: True
        ignore_updates: False
        install_dir: .
        last_update: '0001-01-01T00:00:00'
        repository: R2Northstar/Northstar
"""
    conf_comments = ruamel.yaml.load(default_conf, ruamel.yaml.RoundTripLoader)
else:
    with open("manager_config.yaml", "r") as f:
        conf_comments = yaml.load(f)

config = confuse.Configuration("NorthstarManager", __name__)
config.set(conf_comments)

try:
    for i in ["Manager", "Launcher", "Mods"]:
        config.keys().remove(i)
except ValueError:
    print(f"[{time.strftime('%H:%M:%S')}] [warning] 'manager_config.yaml' is empty or invalid")


git_token = config['Global']['github_token'].get(confuse.Optional(str, default=""))
try:
    if len(git_token) == 0:
        g = Github()
        print(f"[{time.strftime('%H:%M:%S')}] [info]    No configurated github_token, running with a rate limit of {g.rate_limiting[0]}/{g.rate_limiting[1]}")
    else:
        g = Github(git_token)
        print(f"[{time.strftime('%H:%M:%S')}] [info]    Using configurated github_token, running with a rate limit of {g.rate_limiting[0]}/{g.rate_limiting[1]}")
except BadCredentialsException:
    print(f"[{time.strftime('%H:%M:%S')}] [warning] GitHub Token invalid or maybe expired. Check on https://github.com/settings/tokens")
    git_token = ""
    g = Github()
    print(f"[{time.strftime('%H:%M:%S')}] [info]    Using no GitHub Token, running with a rate limit of {g.rate_limiting[0]}/{g.rate_limiting[1]}")

script_queue = []


def printhelp():
    print(f"[{time.strftime('%H:%M:%S')}] [info]    Printing help")
    print(
        "Launch arguments can be set in the 'config_updater.ini'. List of launch arguments:\n"
        "-help ..................... Prints the help section for NorthstarManager.\n"
        "-updateAll ................ Force updates all repos defined in the 'config_updater.ini' to the latest release regardless of the latest release maybe being already installed, ignoring config flags: 'ignore_updates'.\n"
        "-updateAllIgnoreManager ... Force updates all repos defined in the 'config_updater.ini', except the Manager section, to the latest release regardless of the latest release maybe being already installed, ignoring config flags: 'ignore_updates'.\n"
        "-updateServers ............ Force updates all repos defined in the 'config_updater.ini' under the Servers section.\n"
        "-updateClient ............. Force updates all repos defined in the 'config_updater.ini' under the Manager and Mods section.\n"
        "-onlyCheckAll ............. Runs the updater over all repos defined in the 'config_updater.ini' without launching the defined launcher in the 'manager_conf.ymal'.\n"
        "-onlyCheckServers ......... Runs the updater over all repos defined in the 'config_updater.ini' under section Servers without launching the defined launcher in the 'manager_conf.ymal'.\n"
        "-onlyCheckClient .......... Runs the updater over all repos defined in the 'config_updater.ini' under section Manager and Mods without launching the defined launcher in the 'manager_conf.ymal'.\n"
        "-onlyLaunch ............... Only launches the defined file from the Launcher section, without checking fpr updates.\n"
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
    print(f"[{time.strftime('%H:%M:%S')}] [info]    Successfully copied TF2 files")


def sort_gitrelease(release: GitRelease):
    return release.published_at


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
        self.ignore_prerelease = yamlpath["ignore_prerelease"].get(confuse.Optional(bool, default=True))
        self.install_dir = Path(yamlpath["install_dir"].get(confuse.Optional(str, default=".")))
        self._file = yamlpath["file"].get(confuse.Optional(str, default="NorthstarController.exe"))
        self.file = (self.install_dir / self._file).resolve()

    @property
    def last_update(self):
        return datetime.fromisoformat(str(
            self.yamlpath["last_update"].get(confuse.Optional(str, default=datetime.min.isoformat()))))

    @last_update.setter
    def last_update(self, value: datetime):
        config.get()[self.blockname]["last_update"] = value.isoformat()

    def release(self):
        releases = list(self.repo.get_releases())
        releases.sort(reverse=True, key=sort_gitrelease)
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
        if self.ignore_updates and not updateAll and not updateClient:
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Search stopped for new releases  for {self.blockname}")
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

        pass_args = " -onlyCheckAll" if onlyCheckAll else ""
        pass_args += " -updateAllIgnoreManager" if updateAll else ""
        pass_args += " ".join(sys.argv[1:])
        print("pass args for reboot not working porperly")
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
        serverpath = ''
        pre_index = ''
        for index in path:
            if pre_index == "Servers":
                serverpath = Path(config[pre_index][index]["dir"].get(confuse.Optional(str, default=".")))
            yamlpath = yamlpath[index]

        self.yamlpath = yamlpath
        self.blockname = path[-1]
        self.ignore_updates = self.yamlpath["ignore_updates"].get(confuse.Optional(bool, default=False))
        self.ignore_prerelease = (self.yamlpath["ignore_prerelease"].get(confuse.Optional(bool, default=True)))
        self.repository = self.yamlpath["repository"].get()
        self.install_dir = Path(serverpath).joinpath(self.yamlpath["install_dir"].get(confuse.Optional(str, default="./R2Northstar/mods")))  # check if server mods don't get installed under client location
        self._file = self.yamlpath["file"].get(confuse.Optional(str, default="mod.json"))
        self.file = (self.install_dir / self._file).resolve()
        self.exclude_files = self.yamlpath["exclude_files"].get(confuse.Optional(list, default=[]))
        try:
            self.repo = g.get_repo(self.repository)
            self.is_github = True
        except UnknownObjectException:
            self.repo = "https://northstar.thunderstore.io/api/experimental/package/"+self.repository
            self.is_github = False

    @property
    def last_update(self):
        return datetime.fromisoformat(str(
            self.yamlpath["last_update"].get(confuse.Optional(str, default=str(datetime.min.isoformat())))))

    @last_update.setter
    def last_update(self, value: datetime):
        self.yamlpath.get()["last_update"] = value.isoformat()

    def release(self):
        releases = list(self.repo.get_releases())
        releases.sort(reverse=True, key=sort_gitrelease)
        for release in releases:
            if release.prerelease and self.ignore_prerelease:
                continue
            if updateAll \
                    or updateServers \
                    or updateAllIgnoreManager \
                    or release.published_at > self.last_update:
                return release
            if self._file != "mod.json":
                if not self.file.exists() or self._file != "NorthstarLauncher.exe":
                    return release
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
        if self.ignore_updates and not updateAllIgnoreManager and not updateClient:
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Search stopped for new releases  for {self.blockname}")
            return
        try:
            if self.is_github:
                release = self.release()
                url = self.asset(release)
            else:
                t = datetime.fromisoformat(str(requests.get(self.repo).json()["latest"]["date_created"]).split(".")[0])
                if updateAllIgnoreManager\
                        or updateServers\
                        or updateClient\
                        or t > self.last_update:
                    url = requests.get(self.repo).json()["latest"]["download_url"]
                else:
                    raise NoValidRelease("Found No new releases")
            with tempfile.NamedTemporaryFile() as download_file:
                download(url, download_file)
                release_zip = zipfile.ZipFile(download_file)
                self.extract(release_zip)
                if self.is_github:
                    self.last_update = release.published_at
                else:
                    self.last_update = datetime.fromisoformat(str(requests.get(self.repo).json()["latest"]["date_created"]).split(".")[0])
                print(f"[{time.strftime('%H:%M:%S')}] [info]    Installed successfully update    for {self.blockname}")

        except NoValidRelease:
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Latest Version already installed for {self.blockname}")
            return
        except NoValidAsset:
            print(f"[{time.strftime('%H:%M:%S')}] [warning] Possibly faulty        release   for {self.blockname} published Version {release.tag_name} has no valit assets")
            return


def main():
    try:
        if showhelp:
            printhelp()
            return

        if onlyLaunch:
            launcher()
            return

        while not updater():  # restart when encountering a GitHub rate error
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Waiting and restarting Updater in 60s...")
            time.sleep(60)

        if not onlyCheckAll\
                and not onlyCheckClient\
                and not onlyCheckServers:
            launcher()
    except HaltandRunScripts:
        for script in script_queue:
            subprocess.Popen(script, cwd=str(Path.cwd()), shell=True)


def updater() -> bool:
    yamlpath = []
    for section in [s for s in config.keys() if s not in ["Example", "Launcher"]]:
        try:
            if section == "Manager" and not updateAllIgnoreManager and not onlyCheckServers and not updateServers:
                yamlpath = [section]
                print(f"[{time.strftime('%H:%M:%S')}] [info]    Searching for      new releases  for {'/'.join(yamlpath)}...")
                ManagerUpdater(yamlpath).run()
            if section == "Mods" and not onlyCheckServers and not updateServers:
                for mod in config[section]:
                    yamlpath = [section, mod]
                    print(f"[{time.strftime('%H:%M:%S')}] [info]    Searching for      new releases  for {'/'.join(yamlpath)}...")
                    ModUpdater(yamlpath).run()
            if (section == "Servers" and not onlyCheckClient and not updateClient) or \
                    (section == "Servers" and updateServers):
                if not updateServers:
                    if not config[section]["enabled"].get(confuse.Optional(bool, default=True)) and not updateAllIgnoreManager:
                        print(f"[{time.strftime('%H:%M:%S')}] [info]    Searvers are disabled.")
                        continue
                for server in config[section]:
                    if server != "enabled":
                        if not updateServers and not updateAllIgnoreManager:
                            if not config[section][server]["enabled"].get(confuse.Optional(bool, default=True)):
                                print(f"[{time.strftime('%H:%M:%S')}] [info]    Searver {server} is disabled.")
                                continue
                        for mod in config[section][server]["Mods"]:
                            yamlpath = [section, server, "Mods", mod]
                            print(f"[{time.strftime('%H:%M:%S')}] [info]    Searching for      new releases  for {'/'.join(yamlpath)}...")
                            ModUpdater(yamlpath).run()

                        server_path = Path(config[section][server]["dir"].get(confuse.Optional(str, default=f"./servers/{server}")))
                        if not server_path.joinpath("Titanfall2.exe").exists():
                            print(f"[{time.strftime('%H:%M:%S')}] [warning] Titanfall2 files not existing at the server location.")
                            install_tf2(server_path)

        except RateLimitExceededException:
            print(f"[{time.strftime('%H:%M:%S')}] [warning] GitHub rate exceeded for {'/'.join(yamlpath)}")
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Available requests left {g.rate_limiting[0]}/{g.rate_limiting[1]}")
            if "y" != input("Wait and try update again in 60sec? (y/n) "):
                break
            return False
        except FileNotInZip:
            print(
                f"[{time.strftime('%H:%M:%S')}] [warning] Zip file for {'/'.join(yamlpath)} doesn't contain expected files")
    print(f"[{time.strftime('%H:%M:%S')}] [info]    Successfully checkt all mods")
    return True


def launcher():
    script = "C:/Program Files (x86)/Origin/Origin.exe"
    try:
        if "Origin.exe" not in (p.name() for p in psutil.process_iter()):
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Launching Origin and waiting 10sec...")
            subprocess.Popen(script, cwd=str(Path.cwd()), shell=True)
            time.sleep(10)
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Launched  Origin succesfull")

        script = f'"{config["Launcher"]["filename"].get()}" {config["Launcher"]["argumnets"].get()} {" ".join(sys.argv[1:])}'
        print(f"[{time.strftime('%H:%M:%S')}] [info]    Launching {script}")
        subprocess.Popen(script, cwd=str(Path.cwd()), shell=True)

    except FileNotFoundError:
        print(f"[{time.strftime('%H:%M:%S')}] [warning] Could not run {script}")


main()
with open("manager_config.yaml", "w+") as f:
    yaml.dump(conf_comments, f)
