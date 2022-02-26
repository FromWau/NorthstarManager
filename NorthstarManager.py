import json
import confuse
import ruamel.yaml

import psutil
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import time
from datetime import datetime, timedelta

from ruamel.yaml.constructor import DuplicateKeyError
from tqdm import tqdm
import requests
from github import Github
from github.GitRelease import GitRelease

from confuse import ConfigTypeError
from github.GithubException import RateLimitExceededException, BadCredentialsException, UnknownObjectException

# ================
# Read Launch Args
# ================
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

noLaunch = False  # runs the check for updates on the client and servers
try:
    i = sys.argv.index("-noLaunch")
    args += " " + sys.argv.pop(i)
    noLaunch = True
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

launchServers = False  # launches all servers which are not disabled
try:
    i = sys.argv.index("-launchServers")
    args += " " + sys.argv.pop(i)
    launchServers = True
except ValueError:
    pass

launchClient = False  # launches all servers which are not disabled
try:
    i = sys.argv.index("-launchServers")
    args += " " + sys.argv.pop(i)
    launchServers = True
except ValueError:
    pass

print(f"[{time.strftime('%H:%M:%S')}] [info]    Launched NorthstarManager with {'no args' if len(args) == 0 else 'arguments:' + args}")

# =======================================================
# Read 'manager_config.yaml' and setup configuration file
# =======================================================
yaml = ruamel.yaml.YAML()
yaml.indent(mapping=4, sequence=2, offset=0)
global conf_comments

print(f"[{time.strftime('%H:%M:%S')}] [info]    Reading config from 'manager_config.yaml'...")
if not Path("manager_config.yaml").exists():
    print(f"[{time.strftime('%H:%M:%S')}] [warning] 'manager_config.yaml' does not exist")
    print(f"[{time.strftime('%H:%M:%S')}] [info]    Using default config instead")

    # default config if the 'manager_config.yaml' does not exist
    default_conf = """\
# Global - Settings which persist for every other section
# ======================================================
Global:
    github_token:  # token for GitHub, can be acquired from: https://github.com/settings/tokens

# Launcher - Defines the to be launched Application with optional args
# ====================================================================
Launcher:
    filename: NorthstarLauncher.exe  # launches the NorthstarLauncher
#    filename: Titanfall2.exe  # launches Vanilla Titanfall2
    argumnets: ''  # Arguments for the launcher. The NorthstarLauncher uses also the args defined in the ns_startup_args.txt file

# Manager - Config for the Manager of Northstar
# =============================================
Manager:
    repository: FromWau/NorthstarManager  # repo from where to search for updates. Will search at first at GitHub.com and then at northstar.thunderstore.io
    last_update: '0001-01-01T00:00:00'  # publishe date of the latest version of the repo
    file: NorthstarManager.exe  # main file of the repo
#    install_dir: .  # install directory
#    ignore_updates: true  # will ignore new version and keeps the installed version
#    ignore_prerelease: true  # will ignore pre_releases when searching for new realeses of the repo

# Mods - List of managed mods
# ===========================
Mods:
    Northstar:  # Northstar will be handled here
        repository: R2Northstar/Northstar  # repo of Northstar
        last_update: '0001-01-01T00:00:00'  # publishe date of the latest version of Northstar
        install_dir: .  # install directory is necessary for Northstar default is in the mods folder
        file: NorthstarLauncher.exe  # main file of the repo
        exclude_files:  # files that should be excluded when updating the repo
        - ns_startup_args.txt
        - ns_startup_args_dedi.txt


#    How to install a new mod (example for SpeedOMeter) :
#    -------------------------
#    S2speedometer:  # Name of Mod (could be anything)
#        repository: Mysterious_Reuploads/S2speedometer  # the repo from where to grab the latest release

# Servers - List of all Servers that should be managed
# ====================================================
#Servers:
#    enabled: false  # disables all listed servers for update checks, and they will not get launched
#
#    How to install/ configure a server (you do not need to download or setup anything just configure what you want down below) (example for Kraber9k Server):
#    -----------------------------------
#    Kraber 9k:  # Name of the Server
#        dir: servers/Kraber 9k  # directory where the server is located
#        enabled: false  # disables this server for update checks, and the server will not get launched
#        Mods:  # Mods for the server
#            Northstar:  # Northstar, is needed for the server
#                repository: R2Northstar/Northstar  # repo of Northstar
#                last_update: '0001-01-01T00:00:00'  # publishe date of the latest version of Northstar
#                install_dir: .  # install directory from the root dir of the server
#                file: NorthstarLauncher.exe  # main file of the repo
#
#        config:  # Config of the Server, configuration for servers is split up into 3 different files
#            ns_startup_args_dedi.txt: +mp_gamemode ps +setplaylistvaroverride "custom_air_acc_pilot 9000" +setplaylist private_match  # startup args for this server
#            mod.json:  # config for Northstar.CustomServers
#                ConVars:  # the section of the file
#                    ns_private_match_last_map: mp_glitch  # key and value of a configuration
#                    ns_private_match_last_mode: ps
#                    ns_disallowed_weapons: mp_weapon_r97,mp_weapon_alternator_smg,mp_weapon_car,mp_weapon_hemlok_smg,mp_weapon_lmg,mp_weapon_lstar,mp_weapon_esaw,mp_weapon_rspn101,mp_weapon_vinson,mp_weapon_hemlok,mp_weapon_g2,mp_weapon_shotgun,mp_weapon_mastiff,mp_weapon_dmr,mp_weapon_doubletake,mp_weapon_epg,mp_weapon_smr,mp_weapon_pulse_lmg,mp_weapon_softball,mp_weapon_autopistol,mp_weapon_semipistol,mp_weapon_wingman,mp_weapon_shotgun_pistol,mp_weapon_rocket_launcher,mp_weapon_arc_launcher,mp_weapon_defender,mp_weapon_mgl,mp_weapon_wingman_n,mp_weapon_rspn101_og
#                    ns_disallowed_weapon_primary_replacement: mp_weapon_sniper
#            autoexec_ns_server.cfg:  # config for server
#                ns_server_name: Example Kraber9k Server  # key and value of a configuration
#                ns_server_desc: Example Server configurated via FromWau/NorthstarManager
#                ns_should_return_to_lobby: 1
#                ns_private_match_only_host_can_change_settings: 2
#                ns_player_auth_port: 8081  # IMPORTANT: EVERY RUNNING SERVER NEEDS AN UNIQUE PORT AND THIS PORT NEEDS TO BE PORT-FORWARDED 
"""
    conf_comments = ruamel.yaml.load(default_conf, ruamel.yaml.RoundTripLoader)
else:
    try:
        with open("manager_config.yaml", "r") as f:
            conf_comments = yaml.load(f)
    except DuplicateKeyError as e:
        print(f"[{time.strftime('%H:%M:%S')}] [error]   'manager_config.yaml' is invalid. Duplicate Key{e.problem_mark} found")
        exit(1)

config = confuse.Configuration("NorthstarManager", __name__)
config.set(conf_comments)


# ====================
# validates the config
# ====================
def valid_min_conf() -> bool:
    print(f"[{time.strftime('%H:%M:%S')}] [info]    Validating 'manager_config.yaml'...")
    valid_test = {
        'Launcher': {
            'filename': 'NorthstarLauncher.exe',
        },
        'Manager': {
            'repository': 'FromWau/NorthstarManager',
            'file': 'NorthstarManager.exe',
        },
        'Mods': {
            'Northstar': {
                'repository': 'R2Northstar/Northstar',
                'install_dir': '.',
                'file': 'NorthstarLauncher.exe'
            }
        }
    }
    valid_keys = None
    valid_sections = None
    valid_counter = 0
    try:
        for valid_keys in valid_test.keys():
            for valid_sections in valid_test[valid_keys]:
                if (f"{valid_sections}", f"{valid_test[valid_keys][valid_sections]}") in config.get()[valid_keys].items():
                    valid_counter += 1
                    continue
                for valid_subsection in valid_test[valid_keys][valid_sections]:
                    if (f"{valid_subsection}", f"{valid_test[valid_keys][valid_sections][valid_subsection]}") in config.get()[valid_keys][valid_sections].items():
                        valid_counter += 1
        if valid_counter < 6:
            print(f"[{time.strftime('%H:%M:%S')}] [error]   'manager_config.yaml' is empty or invalid")
            return False
        print(f"[{time.strftime('%H:%M:%S')}] [info]    Validation successful for 'manager_config.yaml'")
        return True

    except (TypeError, AttributeError, KeyError):
        print(f"[{time.strftime('%H:%M:%S')}] [error]   'manager_config.yaml' is missing the section {'/'.join([valid_keys, valid_sections])}")
        return False


# Check if loaded conf is valid/ minimal conf is given to run northstar
if not valid_min_conf():
    exit(1)

# ===========================
# Read token and setup githuh
# ===========================
git_token = config['Global']['github_token'].get(confuse.Optional(str, default=""))
try:
    if len(git_token) == 0:
        g = Github()
        print(
            f"[{time.strftime('%H:%M:%S')}] [info]    No configurated github_token, running with a rate limit of {g.rate_limiting[0]}/{g.rate_limiting[1]}")
    else:
        g = Github(git_token)
        print(
            f"[{time.strftime('%H:%M:%S')}] [info]    Using configurated github_token, running with a rate limit of {g.rate_limiting[0]}/{g.rate_limiting[1]}")
except BadCredentialsException:
    print(
        f"[{time.strftime('%H:%M:%S')}] [warning] GitHub Token invalid or maybe expired. Check on https://github.com/settings/tokens")
    git_token = ""
    g = Github()
    print(
        f"[{time.strftime('%H:%M:%S')}] [info]    Using no GitHub Token, running with a rate limit of {g.rate_limiting[0]}/{g.rate_limiting[1]}")

script_queue = []


# ===============
# Prints the help
# ===============
def printhelp():
    print(f"[{time.strftime('%H:%M:%S')}] [info]    Printing help")
    print(
        "Launch arguments can be set in the 'manager_config.yaml'. List of launch arguments:\n"
        "-help ..................... Prints the help section for NorthstarManager.\n"
        "-updateAll ................ Force updates all repos defined in the 'manager_config.yaml' to the latest release regardless of the latest release maybe being already installed, ignoring config flags: 'ignore_updates'.\n"
        "-updateAllIgnoreManager ... Force updates all repos defined in the 'manager_config.yaml', except the Manager section, to the latest release regardless of the latest release maybe being already installed, ignoring config flags: 'ignore_updates'.\n"
        "-updateServers ............ Force updates all repos defined in the 'manager_config.yaml' under the Servers section.\n"
        "-updateClient ............. Force updates all repos defined in the 'manager_config.yaml' under the Manager and Mods section.\n"
        "-noLaunch ............. Runs the updater over all repos defined in the 'manager_config.yaml' without launching the defined launcher in the 'manager_conf.ymal'.\n"
        "-onlyCheckServers ......... Runs the updater over all repos defined in the 'manager_config.yaml' under section Servers without launching the defined launcher in the 'manager_conf.ymal'.\n"
        "-onlyCheckClient .......... Runs the updater over all repos defined in the 'manager_config.yaml' under section Manager and Mods without launching the defined launcher in the 'manager_conf.ymal'.\n"
        "-onlyLaunch ............... Only launches the defined file from the Launcher section, without checking fpr updates.\n"
        "-launchServers ............ Launches all enabled servers from the 'manager_config.yaml'"
        "\n"
        "Northstar Client/ vanilla TF2 args should be put into the ns_startup_args.txt or ns_startup_args_dedi.txt for dedicated servers\n"
        "All Northstar launch arguments can be found at the official wiki: https://r2northstar.gitbook.io/r2northstar-wiki/using-northstar/launch-arguments \n"
        "All vanilla TF2 launch arguments can be found at the source wiki: https://developer.valvesoftware.com/wiki/Command_Line_Options#Command-line_parameters \n"
    )


# ======================
# Download fun for files
# ======================
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


# ====================================
# Copy Titanfall2 files to a given dir
# ====================================
def install_tf2(installpath):
    originpath = Path.cwd()
    print(
        f"[{time.strftime('%H:%M:%S')}] [info]    Copying TF2 files and creating a junction for vpk, r2 to {installpath.absolute()}")
    script = \
        f'xcopy "{originpath.joinpath("__Installer")}" "{installpath.joinpath("__Installer/")}" /E /I /Y /Q >nul 2>&1 && ' \
        f'xcopy "{originpath.joinpath("bin")}" "{installpath.joinpath("bin/")}" /E /I /Y /Q >nul 2>&1 && ' \
        f'xcopy "{originpath.joinpath("Core")}" "{installpath.joinpath("Core/")}" /E /I /Y /Q >nul 2>&1 && ' \
        f'xcopy "{originpath.joinpath("platform")}" "{installpath.joinpath("platform/")}" /E /I /Y /Q >nul 2>&1 && ' \
        f'xcopy "{originpath.joinpath("Support")}" "{installpath.joinpath("Support/")}" /E /I /Y /Q >nul 2>&1 && ' \
        f'xcopy "{originpath.joinpath("build.txt")}" "{installpath}" /Y /Q >nul 2>&1 && ' \
        f'xcopy "{originpath.joinpath("server.dll")}" "{installpath}" /Y /Q >nul 2>&1 && ' \
        f'xcopy "{originpath.joinpath("Titanfall2.exe")}" "{installpath}" /Y /Q >nul 2>&1 && ' \
        f'xcopy "{originpath.joinpath("Titanfall2_trial.exe")}" "{installpath}" /Y /Q >nul 2>&1 && ' \
        f'mklink /j "{installpath.joinpath("vpk")}" "{originpath.joinpath("vpk")}" >nul 2>&1 && ' \
        f'mklink /j "{installpath.joinpath("r2")}" "{originpath.joinpath("r2")}" >nul 2>&1 '
    subprocess.Popen(script, cwd=str(Path.cwd()), shell=True).wait()
    print(f"[{time.strftime('%H:%M:%S')}] [info]    Successfully copied TF2 files")


# =======================================================
# Sort GitRelases after pulished Date (idk how to lambda) %TODO
# =======================================================
def sort_gitrelease(release: GitRelease):
    return release.published_at


# ==========
# Exceptions
# ==========
class NoValidRelease(Exception):
    pass


class NoValidAsset(Exception):
    pass


class FileNotInZip(Exception):
    pass


class HaltandRunScripts(Exception):
    pass


# =====================================
# Handles the updating for this program
# =====================================
class ManagerUpdater:
    def __init__(self, path):
        try:
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
        except ConfigTypeError:
            print(
                f"[{time.strftime('%H:%M:%S')}] [error]   'manager_config.yaml' is invalid at section: {'/'.join(path)}")
            quit(1)

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

        pass_args = " -noLaunch" if noLaunch else ""
        pass_args += " -updateAllIgnoreManager" if updateAll else ""
        pass_args += " ".join(sys.argv[1:])
        script_queue.append(
            f"echo [{time.strftime('%H:%M:%S')}] [info]    Running self-replacer            for {self.blockname} && "
            f"timeout /t 5 && "
            f'del "{self.file}" >nul 2>&1 && '
            f'move "{newfile}" "{self.file}" >nul 2>&1 && '
            f"echo [{time.strftime('%H:%M:%S')}] [info]    Installed successfully update    for {self.blockname} && "
            f"echo [{time.strftime('%H:%M:%S')}] [info]    Launching latest install         of  {self.file.name}{pass_args} && "
            f'"{self.file.name}"{pass_args}'
        )
        raise HaltandRunScripts("restart manager")


# =============================
# Handles the updating for mods
# =============================
class ModUpdater:
    def __init__(self, path):
        try:
            serverpath = ""
            if path[0] == "Servers":
                serverpath = Path(config[path[0]][path[1]]["dir"].get(confuse.Optional(str, default=".")))
            yamlpath = config
            for index in path:
                yamlpath = yamlpath[index]

            self.yamlpath = yamlpath
            self.blockname = path[-1]
            self.ignore_updates = self.yamlpath["ignore_updates"].get(confuse.Optional(bool, default=False))
            self.ignore_prerelease = (self.yamlpath["ignore_prerelease"].get(confuse.Optional(bool, default=True)))
            self.repository = self.yamlpath["repository"].get()
            if len(str(serverpath)) != 0:
                self.install_dir = Path(
                    serverpath / self.yamlpath["install_dir"].get(confuse.Optional(str, default="./R2Northstar/mods")))
            else:
                self.install_dir = Path(
                    self.yamlpath["install_dir"].get(confuse.Optional(str, default="./R2Northstar/mods")))
            self._file = self.yamlpath["file"].get(confuse.Optional(str, default="mod.json"))
            self.file = (self.install_dir / self._file).resolve()
            self.exclude_files = self.yamlpath["exclude_files"].get(confuse.Optional(list, default=[]))
            try:
                self.repo = g.get_repo(self.repository)
                self.is_github = True
            except UnknownObjectException:
                self.repo = "https://northstar.thunderstore.io/api/experimental/package/" + self.repository
                self.is_github = False
        except ConfigTypeError:
            print(
                f"[{time.strftime('%H:%M:%S')}] [error]   'manager_config.yaml' is invalid at section: {'/'.join(path)}")
            quit(1)

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
                if updateAllIgnoreManager \
                        or updateServers \
                        or updateClient \
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
                    self.last_update = datetime.fromisoformat(
                        str(requests.get(self.repo).json()["latest"]["date_created"]).split(".")[0])
                print(f"[{time.strftime('%H:%M:%S')}] [info]    Installed successfully update    for {self.blockname}")

        except NoValidRelease:
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Latest Version already installed for {self.blockname}")
            return
        except NoValidAsset:
            print(
                f"[{time.strftime('%H:%M:%S')}] [warning] Possibly faulty        release   for {self.blockname} published Version {release.tag_name} has no valit assets")
            return


# ====
# main
# ====
def main():
    # prints help
    if showhelp:
        printhelp()
        return

    # only launches the defined launcher
    if onlyLaunch:
        launcher()
        return

    # check for updates/ manages updates / installs updates
    try:
        # restart updater when encountering a GitHub rate error
        while not updater():
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Waiting and restarting Updater in 60s...")
            time.sleep(60)
    except HaltandRunScripts:
        for script in script_queue:
            subprocess.Popen(script, cwd=str(Path.cwd()), shell=True)
        return

        # launches all enabled servers
    if launchServers:
        launchservers()

    # check if allowed to launch the launcher
    if not noLaunch:
        launcher()


# =================================
# reads config and performs updates
# =================================
def updater() -> bool:
    for section in [s for s in config.keys() if s not in ["Launcher"]]:
        yamlpath = [section]
        try:
            if section == "Manager" and not updateAllIgnoreManager and not onlyCheckServers and not updateServers:
                if config[section].get() is None:
                    print(
                        f"[{time.strftime('%H:%M:%S')}] [warning] {'/'.join(yamlpath)} does not have subsections defined")
                    return True
                print(
                    f"[{time.strftime('%H:%M:%S')}] [info]    Searching for      new releases  for {'/'.join(yamlpath)}...")
                ManagerUpdater(yamlpath).run()
            if section == "Mods" and not onlyCheckServers and not updateServers:
                if config[section].get() is None:
                    print(
                        f"[{time.strftime('%H:%M:%S')}] [warning] {'/'.join(yamlpath)} does not have subsections defined")
                    return True
                for mod in config[section]:
                    yamlpath = [section, mod]
                    print(
                        f"[{time.strftime('%H:%M:%S')}] [info]    Searching for      new releases  for {'/'.join(yamlpath)}...")
                    ModUpdater(yamlpath).run()
            if (section == "Servers" and not onlyCheckClient and not updateClient) or \
                    (section == "Servers" and updateServers):
                if config[section].get() is None:
                    print(
                        f"[{time.strftime('%H:%M:%S')}] [warning] Skipping Section {'/'.join(yamlpath)}, config is invalid/ is missing subsections")
                    return True
                if not updateServers:
                    if not config[section]["enabled"].get(
                            confuse.Optional(bool, default=True)) and not updateAllIgnoreManager:
                        print(f"[{time.strftime('%H:%M:%S')}] [info]    Searvers are disabled.")
                        continue
                for server in config[section]:
                    if server != "enabled":
                        if config[section].get() is None:
                            print(
                                f"[{time.strftime('%H:%M:%S')}] [warning] {'/'.join(yamlpath)} does not have subsections defined")
                            return True
                        if not updateServers and not updateAllIgnoreManager:
                            if not config[section][server]["enabled"].get(confuse.Optional(bool, default=True)):
                                print(f"[{time.strftime('%H:%M:%S')}] [info]    Searver {server} is disabled.")
                                continue
                        server_path = Path(
                            config[section][server]["dir"].get(confuse.Optional(str, default=f"./servers/{server}")))

                        if not server_path.joinpath("Titanfall2.exe").exists():
                            print(f"[{time.strftime('%H:%M:%S')}] [warning] Titanfall2 files invalid or don't exists at the server location")
                            install_tf2(server_path)

                        for con in config[section][server]:
                            if con == "Mods":
                                for mod in config[section][server][con]:
                                    yamlpath = [section, server, con, mod]
                                    print(
                                        f"[{time.strftime('%H:%M:%S')}] [info]    Searching for      new releases  for {'/'.join(yamlpath)}...")
                                    ModUpdater(yamlpath).run()
                            elif con == "config":
                                for file in config[section][server][con]:
                                    yamlpath = [section, server, con, file]

                                    if file == "ns_startup_args_dedi.txt":
                                        x = Path(server_path / file)
                                        if not x.exists():
                                            print(
                                                f"[{time.strftime('%H:%M:%S')}] [warning] file in config: {'/'.join(yamlpath)} not found. check spelling or run the manager with -updateServers if northstar is not installed")

                                        replace_str = ""
                                        config_list = str(config[section][server][con][file].get()).strip() + " "
                                        c_dict = {}
                                        for c in list(config_list.split("+")[1:]):
                                            c.strip()
                                            split = c.split(" ")
                                            c_dict["+" + split[0]] = split[1] if len(split[1:-1]) == 1 else " ".join(
                                                split[1:-1])

                                        with open(x, 'r') as replace:
                                            while line := replace.readline():
                                                line = line.strip()
                                                va = list(line.split("+")[1:])
                                                for line_value in va:
                                                    split = line_value.split(" ")
                                                    key = "+" + split[0]
                                                    va = split[1] if len(split[1:-1]) == 1 else " ".join(split[1:-1])

                                                    if key in c_dict.keys():
                                                        continue
                                                    replace_str += f" {key} {va}"

                                        for k, v in c_dict.items():
                                            replace_str += f" {k} {v}"
                                        replace_str = replace_str.strip()

                                        # write new config to file
                                        with open(x, "w") as replace:
                                            replace.write(replace_str)

                                    elif file == "mod.json":
                                        for file_section in config[section][server][con][file]:
                                            yamlpath = [section, server, con, file, file_section]
                                            if file_section == "ConVars":

                                                x = Path(
                                                    server_path / "R2Northstar/mods/Northstar.CustomServers" / file)
                                                if not x.exists():
                                                    print(
                                                        f"[{time.strftime('%H:%M:%S')}] [warning] file in config: {'/'.join(yamlpath)} not found. check spelling or run the manager with -updateServers if northstar is not installed")

                                                config_list = config[section][server][con][file][file_section].get()
                                                # read config
                                                with open(x, "r") as j:
                                                    data = json.load(j)

                                                json_list = list(data["ConVars"])
                                                remove_list = []
                                                # search the to replace items
                                                for j in json_list:
                                                    for key, value in config_list.items():
                                                        if j["Name"] == key:
                                                            remove_list.append(j)
                                                # remove to replace items
                                                for j in remove_list:
                                                    json_list.remove(j)
                                                # add updated item
                                                for key, value in config_list.items():
                                                    json_string = {
                                                        "Name": key,
                                                        "DefaultValue": value
                                                    }
                                                    json_list.append(json_string)
                                                # write config
                                                data["ConVars"] = json_list
                                                with open(x, "w") as j:
                                                    json.dump(data, j, indent=4)

                                            else:
                                                print(f"Unknown section in {yamlpath}")

                                    elif file == "autoexec_ns_server.cfg":
                                        x = Path(
                                            server_path / "R2Northstar/mods/Northstar.CustomServers/mod/cfg" / file)
                                        if not x.exists():
                                            print(
                                                f"[{time.strftime('%H:%M:%S')}] [warning] file in config: {'/'.join(yamlpath)} not found. check spelling or run the manager with -updateServers if northstar is not installed")

                                        replace_str = ""
                                        config_list = config[section][server][con][file].get().copy()

                                        # search for args that need to be replaced
                                        with open(x, 'r') as replace:
                                            while line := replace.readline():
                                                line = line.strip()
                                                if not line:  # for blank lines
                                                    replace_str += "\n"
                                                    continue

                                                if line.startswith("//"):  # for only comment lines
                                                    replace_str += line + "\n"
                                                    continue

                                                comment = line.split(" //")
                                                line_value = comment[0].split(" ")

                                                found = False
                                                for key, value in config_list.items():
                                                    if key == line_value[0]:
                                                        config_list.pop(key)
                                                        found = True
                                                        replace_str += f"{line_value[0]} {value}{'' if len(comment[1:]) == 0 else ' //' + ' '.join(comment[1:])} \n"
                                                        break
                                                if not found:
                                                    replace_str += f"{line_value[0]} {' '.join(line_value[1:])} //{' '.join(comment[1:])}\n"

                                        # add not found args in config file
                                        for key, value in config_list.items():
                                            replace_str += f"{key} {value}\n"

                                        # write new config to file
                                        with open(x, "w") as replace:
                                            replace.write(replace_str)

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


# =============================
# launches the defined launcher
# =============================
def launcher():
    script = f'"{config["Launcher"]["filename"].get()}" {config["Launcher"]["arguments"].get()} {" ".join(sys.argv[1:])}'
    pre_launch_origin()
    try:
        print(f"[{time.strftime('%H:%M:%S')}] [info]    Launching {script}")
        subprocess.Popen(script, cwd=str(Path.cwd()), shell=True)
    except FileNotFoundError:
        print(f"[{time.strftime('%H:%M:%S')}] [warning] Could not run {script}")


# ==================
# prelaunches origin
# ==================
def pre_launch_origin():
    script = "C:/Program Files (x86)/Origin/Origin.exe"
    try:
        if "Origin.exe" not in (p.name() for p in psutil.process_iter()):
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Launching Origin and waiting 10sec...")
            subprocess.Popen(script, cwd=str(Path.cwd()), shell=True)
            time.sleep(10)
            print(f"[{time.strftime('%H:%M:%S')}] [info]    Launched  Origin succesfull")

    except FileNotFoundError:
        print(f"[{time.strftime('%H:%M:%S')}] [warning] Could not run {script}")


# ============================
# launches all enabled servers
# ============================
def launchservers():
    scripts = []

    if not config["Servers"]["enabled"].get(confuse.Optional(bool, default=True)):
        print("Servers are disabled.")
        return
    for server in config["Servers"]:
        if server != "enabled":
            if not config["Servers"][server]["enabled"].get(confuse.Optional(bool, default=True)):
                print(f"{server} is disabled")
                continue
            else:
                print("launch " + server)
                server_dir = config["Servers"][server]["dir"]
                scripts.append(f'start cmd.exe /k "cd /d {server_dir} && NorthstarLauncher.exe -dedicated"')

    if len(scripts) == 0:
        print("No enabled Servers found.")
        return

    pre_launch_origin()
    for script in scripts:
        subprocess.Popen(script, cwd=str(Path.cwd()), shell=True)


main()
# ============
# write config
# ============
with open("manager_config.yaml", "w+") as f:
    yaml.dump(conf_comments, f)
