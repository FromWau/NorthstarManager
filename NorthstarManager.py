import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path

import confuse
import psutil
import requests
import ruamel.yaml
from confuse import ConfigTypeError
from github import Github
from github.GitRelease import GitRelease
from github.GithubException import RateLimitExceededException, BadCredentialsException, UnknownObjectException
from requests import ConnectionError
from ruamel.yaml.constructor import DuplicateKeyError
from ruamel.yaml.parser import ParserError
from ruamel.yaml.scanner import ScannerError
from tqdm import tqdm

# =============
# Logging setup
# =============
logger = logging.getLogger()
streamHandler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    f'[%(asctime)s] [%(levelname)-7s] [{Path(sys.argv[0]).name.split(".")[0]}] %(message)s', datefmt='%H:%M:%S'
)
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)
logger.setLevel(logging.DEBUG)

# ================
# Read Launch Args
# ================
args = ""
sysargs = [sysargs.lower() for sysargs in sys.argv]

showHelp = False  # print help and quit
try:
    i = sysargs.index("-help")
    args += " " + sysargs.pop(i)
    showHelp = True
except ValueError:
    pass

loglevel = []  # forces the logging level
try:
    i = sysargs.index("-debug")
    args += " " + sysargs.pop(i)
    loglevel.append("DEBUG")
except ValueError:
    pass

try:
    i = sysargs.index("-info")
    args += " " + sysargs.pop(i)
    loglevel.append("INFO")
except ValueError:
    pass

try:
    i = sysargs.index("-warning")
    args += " " + sysargs.pop(i)
    loglevel.append("WARNING")
except ValueError:
    pass

try:
    i = sysargs.index("-error")
    args += " " + sysargs.pop(i)
    loglevel.append("ERROR")
except ValueError:
    pass

try:
    i = sysargs.index("-critical")
    args += " " + sysargs.pop(i)
    loglevel.append("CRITICAL")
except ValueError:
    pass

updateAll = False  # Force updates manager then relaunches manager with args -updateAllIgnoreManager
try:
    i = sysargs.index("-updateall")
    args += " " + sysargs.pop(i)
    updateAll = True
except ValueError:
    pass

updateAllIgnoreManager = False  # everything in yaml configurated will get force updated
try:
    i = sysargs.index("-updateallignoremanager")
    args += " " + sysargs.pop(i)
    updateAllIgnoreManager = True
except ValueError:
    pass

updateServers = False  # Force updates servers, ignoring enabled flags
try:
    i = sysargs.index("-updateservers")
    args += " " + sysargs.pop(i)
    updateServers = True
except ValueError:
    pass

updateClient = False  # Force updates client and all the mods of the client, ignoring enabled flags
try:
    i = sysargs.index("-updateclient")
    args += " " + sysargs.pop(i)
    updateClient = True
except ValueError:
    pass

onlyCheckServers = False  # only runs the check for updates on the servers
try:
    i = sysargs.index("-onlycheckservers")
    args += " " + sysargs.pop(i)
    onlyCheckServers = True
except ValueError:
    pass

onlyCheckClient = False  # only runs the check for updates on the client
try:
    i = sysargs.index("-onlycheckclient")
    args += " " + sysargs.pop(i)
    onlyCheckClient = True
except ValueError:
    pass

noUpdates = False  # disables the check for updates
try:
    i = sysargs.index("-noupdates")
    args += " " + sysargs.pop(i)
    noUpdates = True
except ValueError:
    pass

noLaunch = False  # does not launch the client
try:
    i = sysargs.index("-nolaunch")
    args += " " + sysargs.pop(i)
    noLaunch = True
except ValueError:
    pass

launchServers = False  # launches all servers which are not disabled
try:
    i = sysargs.index("-launchservers")
    args += " " + sysargs.pop(i)
    launchServers = True
except ValueError:
    pass

# set log level from args if exists
if len(loglevel) > 0:
    logger.setLevel(logging.getLevelName(str(loglevel[0]).upper()))

logger.info(f"Launched NorthstarManager with {'no args' if len(sysargs) == 0 else f'valid arguments: {args.strip()}'}")

# =======================================================
# Read 'manager_config.yaml' and setup configuration file
# =======================================================
yaml = ruamel.yaml.YAML()
yaml.indent(mapping=4, sequence=2, offset=0)
global conf_comments

logger.info("[Config] Reading config from 'manager_config.yaml'...")
if not Path("manager_config.yaml").exists():
    logger.warning("[Config] 'manager_config.yaml' does not exist. Using default config instead")

    # default config if the 'manager_config.yaml' does not exist
    default_conf = """\
# Global - Settings which persist for every other section
# =======================================================
Global:
    github_token:  # Token for GitHub, can be acquired from: https://github.com/settings/tokens
#    log_level: DEBUG  # Sets the log level. Can be set to CRITICAL, ERROR, WARNING, INFO, DEBUG. Default is INFO

# Launcher - Defines the to be launched Application with optional args
# ====================================================================
Launcher:
    filename: NorthstarLauncher.exe  # launches the NorthstarLauncher
#    filename: Titanfall2.exe  # launches Vanilla Titanfall2
    argumnets: ''  # Arguments for the launcher. Arguments in this file will replace if already existing those in the 'ns_startup_args.txt'

# Manager - Config for the Manager of Northstar
# =============================================
Manager:
    repository: FromWau/NorthstarManager  # repo from where to search for updates. Will search at first at GitHub.com and then at northstar.thunderstore.io
    last_update: '2022-03-17T19:04:38'  # publishe date of the latest version of the repo
#    install_dir: .  # install directory
    file: NorthstarManager.exe  # main file of the repo
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

#    How to configure a new mod (example for CustomScopeFOV) :
#    -------------------------
#    CustomScopeFOV:
#        repository: Avalar/CustomScopeFOV
#        last_update: '0001-01-01T00:00:00'
#        exclude_files:
#        - mod\scripts\weapons\mp_pistols_fov.txt  # specify path to file which should be not excluded from updating

# Servers - List of all Servers that should be managed
# ====================================================
Servers:
    enabled: true  # disables all listed servers for update checks, and they will not get launched
#
#    How to install/ configure a server (you do not need to download or setup anything just configure what you want down below) (example for Kraber9k Server):
#    -----------------------------------
    Kraber 9k:  # Name of the Server
#        dir: servers/Kraber 9k  # directory where the server is located. Default is the yaml path (Servers/Servername).
#        enabled: true  # disables this server for update checks, and the server will not get launched
        Mods:  # Mods for the server
            Northstar:  # Northstar, is needed for the server
                repository: R2Northstar/Northstar  # repo of Northstar
                last_update: '0001-01-01T00:00:00'  # publishe date of the latest version of Northstar
                install_dir: .  # install directory from the logger dir of the server
                file: NorthstarLauncher.exe  # main file of the repo
            # Nice to have Server Mods:
            PlayerVote:
                repository: ScureX/PlayerVote
                last_update: '0001-01-01T00:00:00'
            AntiAFK:
                repository: laundmo/AntiAFK
                last_update: '0001-01-01T00:00:00'
        Config:  # Config of the Server, configuration for servers is split up into 3 different files
            # startup args for this server
            # list of all startup argumnets can be found on the wiki https://r2northstar.gitbook.io/r2northstar-wiki/hosting-a-server-with-northstar/dedicated-server#startup-arguments
            # IMPORTANT: EVERY RUNNING SERVER NEEDS AN UNIQUE UDP PORT (-port xxxxx) AND THIS PORT NEEDS TO BE PORT-FORWARDED IN YOUR ROUTER SETTINGS
            ns_startup_args_dedi.txt: +setplaylist private_match -multiple +mp_gamemode ps +setplaylistvaroverrides "custom_air_accel_pilot 9000" -enablechathooks -softwared3d11 -port 37015

            # Default ConVars for Northstar.CustomServers
            mod.json:
                # ConVars which should be added or overriden
                # list of all convars can be found on the wiki https://r2northstar.gitbook.io/r2northstar-wiki/hosting-a-server-with-northstar/dedicated-server#convars
                ConVars:
                    ns_private_match_last_map: mp_glitch  # key and value of a configuration
                    ns_private_match_last_mode: ps
                    ns_disallowed_weapons: mp_weapon_r97,mp_weapon_alternator_smg,mp_weapon_car,mp_weapon_hemlok_smg,mp_weapon_lmg,mp_weapon_lstar,mp_weapon_esaw,mp_weapon_rspn101,mp_weapon_vinson,mp_weapon_hemlok,mp_weapon_g2,mp_weapon_shotgun,mp_weapon_mastiff,mp_weapon_dmr,mp_weapon_doubletake,mp_weapon_epg,mp_weapon_smr,mp_weapon_pulse_lmg,mp_weapon_softball,mp_weapon_autopistol,mp_weapon_semipistol,mp_weapon_wingman,mp_weapon_shotgun_pistol,mp_weapon_rocket_launcher,mp_weapon_arc_launcher,mp_weapon_defender,mp_weapon_mgl,mp_weapon_wingman_n,mp_weapon_rspn101_og
                    ns_disallowed_weapon_primary_replacement: mp_weapon_sniper
"""
    conf_comments = ruamel.yaml.load(default_conf, ruamel.yaml.RoundTripLoader)
else:
    try:
        with open("manager_config.yaml", "r") as f:
            conf_comments = yaml.load(f)

    except ParserError as e:
        logger.error(f"[Config] 'manager_config.yaml' is invalid.{e.problem_mark} caused a parsing error")
        exit(1)

    except ScannerError as e:
        logger.error(f"[Config] 'manager_config.yaml' is invalid.{e.problem_mark} caused a mapping error")
        exit(1)

    except DuplicateKeyError as e:
        logger.error(f"[Config] 'manager_config.yaml' is invalid. Duplicate Key{e.problem_mark} found")
        exit(1)

config = confuse.Configuration(Path(sys.argv[0]).name.split(".")[0], __name__)
config.set(conf_comments)

# set log level from config if args dont have a specified log level
if len(loglevel) == 0:
    logger.setLevel(
        logging.getLevelName(str(config["Global"]["log_level"].get(confuse.Optional(str, default="INFO"))).upper()))


# ====================
# validates the config
# ====================
def valid_min_conf() -> bool:
    logger.debug("[Config] Running basic validation for 'manager_config.yaml'...")
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
                    if (f"{valid_subsection}", f"{valid_test[valid_keys][valid_sections][valid_subsection]}") in \
                            config.get()[valid_keys][valid_sections].items():
                        valid_counter += 1
        if valid_counter < 6:
            logger.error("[Config] 'manager_config.yaml' is empty or invalid")
            return False
        logger.debug("[Config] 'manager_config.yaml' basic validation successful")
        return True

    except (TypeError, AttributeError, KeyError):
        logger.error(f"[Config] 'manager_config.yaml' is missing the section {'/'.join([valid_keys, valid_sections])}")
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
        logger.info(
            f"[Config] [GitToken] No configurated github_token, running with a rate limit of {g.rate_limiting[0]}/{g.rate_limiting[1]}")
    else:
        g = Github(git_token)
        logger.info(
            f"[Config] [GitToken] Using configurated github_token, running with a rate limit of {g.rate_limiting[0]}/{g.rate_limiting[1]}")
except BadCredentialsException:
    logger.warning(
        f"[Config] [GitToken] GitHub Token invalid or maybe expired. Check on https://github.com/settings/tokens")
    g = Github()
    logger.info(
        f"[Config] [GitToken] Using no GitHub Token, running with a rate limit of {g.rate_limiting[0]}/{g.rate_limiting[1]}")

script_queue = []


# ===============
# Prints the help
# ===============
def printhelp():
    logger.info("[Help] Printing help\n"
                "Launch arguments can be set in the 'manager_config.yaml'. List of launch arguments:\n"
                "-help ..................... Prints the help section for NorthstarManager.\n"
                "-updateAll ................ Force updates all repos defined in the 'manager_config.yaml' to the latest release regardless of the latest release maybe being already installed, ignoring config flags: 'ignore_updates'.\n"
                "-updateAllIgnoreManager ... Force updates all repos defined in the 'manager_config.yaml', except the Manager section, to the latest release regardless of the latest release maybe being already installed, ignoring config flags: 'ignore_updates'.\n"
                "-updateServers ............ Force updates all repos defined in the 'manager_config.yaml' under the Servers section.\n"
                "-updateClient ............. Force updates all repos defined in the 'manager_config.yaml' under the Manager and Mods section.\n"
                "-onlyCheckServers ......... Looks for updates only for repos defined in the 'manager_config.yaml' under section Servers without launching the defined launcher in the 'manager_conf.ymal'.\n"
                "-onlyCheckClient .......... Looks for updates only for repos defined in the 'manager_config.yaml' under section Manager and Mods without launching the defined launcher in the 'manager_conf.ymal'.\n"
                "-noUpdate ................. Only launches the defined file from the Launcher section, without checking fpr updates.\n"
                "-noLaunch ................. Runs the updater over all repos defined in the 'manager_config.yaml' without launching the defined launcher in the 'manager_conf.ymal'.\n"
                "-launchServers ............ Launches all enabled servers from the 'manager_config.yaml'")


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
    yamlpath = str(installpath).replace("\\", "] [")
    logger.info(f"[{yamlpath}] Copying TF2 files and creating a junction for vpk, r2 to {installpath}")

    originpath = Path.cwd()
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
    subprocess.Popen(script, cwd=str(originpath), shell=True).wait()

    logger.info(f"[{yamlpath}] Successfully copied TF2 files")


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


class SectionHasNoSubSections(Exception):
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

            self.path = path
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
            logger.error(f"[{'] ['.join(self.path)}] 'manager_config.yaml' is invalid at section: {'/'.join(path)}")
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
                    release.published_at > self.last_update:

                try:  # if asset not available contine search
                    asset = self.asset(release)
                    logger.info(
                        f"[{'] ['.join(self.path)}] Updating to new release for {self.blockname} published Version {release.tag_name}")
                    return release, asset
                except NoValidAsset as invalid:
                    logger.debug(f"[{'] ['.join(self.path)}] {invalid}")
                    continue

        raise NoValidRelease("No new release found")

    def asset(self, release: GitRelease):
        assets = release.get_assets()
        for asset in assets:
            if asset.content_type in ["application/octet-stream", "application/x-msdownload"]:
                logger.debug(f"[{'] ['.join(self.path)}] Found valid asset {asset}")
                return asset
        raise NoValidAsset(f"No valid asset was found in {release.tag_name}")

    def run(self):
        logger.info(f"[{'] ['.join(self.path)}] Searching for new releases...")

        if self.ignore_updates and not updateAll and not updateClient:
            logger.info(f"[{'] ['.join(self.path)}] Search stopped for new releases  for {self.blockname}")
            return

        tag = ""
        try:
            release, asset = self.release()
            tag = release.tag_name
            url = asset.browser_download_url

        except NoValidRelease:
            logger.info(f"[{'] ['.join(self.path)}] Latest Version already installed for {self.blockname}")
            return
        except NoValidAsset:
            logger.warning(
                f"[{'] ['.join(self.path)}] Possibly faulty release for {self.blockname} published Version {tag} has no valit assets")
            return
        with tempfile.NamedTemporaryFile(delete=False) as download_file:
            logger.info(f"[{'] ['.join(self.path)}] Downloading: {url}")
            download(url, download_file)

        newfile: Path = self.file.with_suffix(".new")
        shutil.move(download_file.name, newfile)
        self.last_update = release.published_at
        logger.info(
            f"[{'] ['.join(self.path)}] Stopped Updater and rerun new Version of {self.blockname} after install")

        pass_args = " -updateAllIgnoreManager" if updateAll else ""
        pass_args += " -updateClient -updateAllIgnoreManager" if updateClient else ""
        pass_args += " -updateServers" if updateServers else ""

        pass_args += " -onlyCheckClient" if onlyCheckClient else ""
        pass_args += " -onlyCheckServers" if onlyCheckServers else ""
        pass_args += " -noUpdates" if noUpdates else ""

        pass_args += " -noLaunch" if noLaunch else ""
        pass_args += " -launchServers" if launchServers else ""

        pass_args += f" -{loglevel[0]}" if len(loglevel) > 0 else ""

        pass_args += " ".join(sys.argv[1::])
        script_queue.append(
            f"echo [{time.strftime('%H:%M:%S')}] [INFO   ] Running self-replacer for {self.blockname} && "
            f"timeout /t 2 /nobreak && "
            f'del "{self.file}" >nul 2>&1 && '
            f'move "{newfile}" "{self.file}" >nul 2>&1 && '
            f"echo [{time.strftime('%H:%M:%S')}] [INFO   ] Installed successfully update for {self.blockname} && "
            f"echo [{time.strftime('%H:%M:%S')}] [INFO   ] Launching latest install of {self.file.name}{pass_args} && "
            f'"{self.file.name}"{pass_args}'
        )
        raise HaltandRunScripts("restart manager")


# =============================
# Handles the updating for mods
# =============================
class ModUpdater:
    def __init__(self, yamlpath):
        try:
            if yamlpath[0] == "Servers":
                serverpath = Path(
                    config[yamlpath[0]][yamlpath[1]]["dir"].get(confuse.Optional(str, default='/'.join(yamlpath[0:2]))))
            else:
                serverpath = Path(".")
            data = config
            for index in yamlpath:
                data = data[index]

            self.yamlpath = yamlpath
            self.data = data
            self.blockname = yamlpath[-1]
            self.ignore_updates = self.data["ignore_updates"].get(confuse.Optional(bool, default=False))
            self.ignore_prerelease = (self.data["ignore_prerelease"].get(confuse.Optional(bool, default=True)))
            self.repository = self.data["repository"].get()
            self.install_dir = Path(serverpath / self.data["install_dir"].get(
                confuse.Optional(str,
                                 default=f"./R2Northstar/mods/{str(self.repository).split('/')[0]}.{str(self.repository).split('/')[1]}")))
            self._file = self.data["file"].get(confuse.Optional(str, default="mod.json"))
            self.file = (self.install_dir / self._file).resolve()
            self.exclude_files = self.data["exclude_files"].get(confuse.Optional(list, default=[]))

            self.repo = f"https://northstar.thunderstore.io/api/experimental/package/{self.repository}"
            if requests.get(self.repo).status_code == 200:
                self.is_github = False
                logger.debug(
                    f"[{'] ['.join(self.yamlpath)}] Using Repo: northstar.thunderstore.io for {self.repository}")

            else:
                try:
                    self.repo = g.get_repo(self.repository)
                    self.is_github = True
                    logger.debug(
                        f"[{'] ['.join(self.yamlpath)}] Using Repo: GitHub for {self.repo}")
                except UnknownObjectException:
                    logger.error(
                        f"[{'] ['.join(self.yamlpath)}] Could not be found in any Repo")

        except ConfigTypeError:
            logger.error(
                f"[{'] ['.join(self.yamlpath)}] 'manager_config.yaml' is invalid at section: {'/'.join(yamlpath)}")
            quit(1)

    @property
    def last_update(self):
        return datetime.fromisoformat(str(
            self.data["last_update"].get(confuse.Optional(str, default=str(datetime.min.isoformat())))))

    @last_update.setter
    def last_update(self, value: datetime):
        self.data.get()["last_update"] = value.isoformat()

    def release(self):
        releases = list(self.repo.get_releases())
        releases.sort(reverse=True, key=sort_gitrelease)
        for release in releases:
            if release.prerelease and self.ignore_prerelease:
                continue

            if updateAll \
                    or updateAllIgnoreManager \
                    or updateServers \
                    or updateClient \
                    or not self.file.exists() \
                    or self._file == "NorthstarLauncher.exe" and (
                    not self.install_dir.joinpath("R2Northstar/mods/Northstar.Client").exists() or
                    not self.install_dir.joinpath("R2Northstar/mods/Northstar.Custom").exists() or
                    not self.install_dir.joinpath("R2Northstar/mods/Northstar.CustomServers").exists()) \
                    or release.published_at > self.last_update:
                return release
        raise NoValidRelease("Found No new releases")

    def asset(self, release: GitRelease) -> str:
        logger.info(
            f"[{'] ['.join(self.yamlpath)}] Updating to new release for {self.blockname} published Version {release.tag_name}")
        assets = release.get_assets()

        if assets.totalCount == 0:  # if no application release exists try download source direct.
            return release.zipball_url
        else:
            for asset in [asset for asset in assets if
                          asset.content_type in ["application/zip", "application/x-zip-compressed"]]:
                return asset.browser_download_url
            raise NoValidAsset("No valid asset was found in release")

    def extract(self, zip_: zipfile.ZipFile):
        # find parent folder of file (e.g. mod.json or NorthstarLauncher.exe)
        namelist = zip_.namelist()
        cwd = None
        for folder in [nlist for nlist in namelist if re.search(f"/{self._file}", nlist) or nlist == self._file]:
            cwd = Path("." if folder == self._file else folder.removesuffix(f"{self._file}"))

        # check if file exists in zip
        if not cwd:
            raise FileNotInZip()

        # if updating northstar backup all mods
        if self.repository == "R2Northstar/Northstar":
            bakmods = cwd.joinpath("R2Northstar\mods")
            if not bakmods.exists():
                logger.debug(
                    f"[{'] ['.join(self.yamlpath)}] Creating Directory {bakmods}")
                os.makedirs("R2Northstar\mods")
            baklst = []
            for mods in bakmods.iterdir():
                if mods.name.startswith("Northstar.") or mods.is_file():
                    continue
                baklst.append(cwd.joinpath(mods))

            if not cwd.joinpath(".bakmods").exists():
                cwd.joinpath(".bakmods").mkdir()

            for mod in baklst:
                shutil.move(cwd.joinpath(mod), cwd.joinpath(".bakmods"))

        # create backup file for excluded files
        for file in [file for file in self.exclude_files if self.install_dir.joinpath(file).exists()]:
            try:
                # if source and destination in same folder aka for Northstar installs
                shutil.copy(self.install_dir.joinpath(file), self.install_dir)
            except shutil.SameFileError:
                pass
            self.install_dir.joinpath(Path(file).name).rename(self.install_dir.joinpath(f"{Path(file).name}.bak"))
            logger.debug(f"[{'] ['.join(self.yamlpath)}] Created {self.install_dir.joinpath(f'{Path(file).name}.bak')}")

        if self.install_dir.joinpath(cwd) == self.install_dir:
            # extract zip into install_dir
            for fileinfo in zip_.infolist():
                zip_.extract(fileinfo.filename, self.install_dir)
                logger.debug(f"[{'] ['.join(self.yamlpath)}] Extract Downloaded zip into {self.install_dir}")

            # move backup file of excluded files if exists
            for file in [file for file in self.exclude_files if Path(f"{Path(file).name}.bak").exists()]:
                newfile = self.install_dir.joinpath(file)
                shutil.move(self.install_dir.joinpath(f"{Path(file).name}.bak"), newfile)
                logger.debug(
                    f"[{'] ['.join(self.yamlpath)}] Replace {newfile} with backup file {self.install_dir.joinpath(f'{Path(file).name}.bak')}")

        else:
            # extract zip with some magic
            for fileinfo in [info for info in zip_.infolist() if info.filename.startswith(cwd.as_posix())]:
                path = fileinfo.filename

                if Path(path).name not in self.exclude_files:
                    zip_.extract(path, self.install_dir)
                    logger.debug(f"[{'] ['.join(self.yamlpath)}] Extract Downloaded zip into {self.install_dir}")
                else:
                    if not Path(path).exists():  # check for first time installation of excluded files
                        zip_.extract(path, self.install_dir)
                        logger.debug(f"[{'] ['.join(self.yamlpath)}] Extract Downloaded zip into {self.install_dir}")

            # delete old files because shutil cant replace-copy
            for replace in [r for r in self.install_dir.iterdir() if
                            r.name != self.install_dir.joinpath(cwd.parts[0]).name]:
                # filter for exclude files
                if replace.name.endswith(".bak"):
                    continue

                if replace.is_dir():
                    shutil.rmtree(replace)
                    logger.debug(f"[{'] ['.join(self.yamlpath)}] Delete old dir {replace}")
                elif replace.is_file():
                    Path.unlink(replace)
                    logger.debug(f"[{'] ['.join(self.yamlpath)}] Delete old file {replace}")

            # copy
            for files in self.install_dir.joinpath(cwd).iterdir():
                shutil.move(files, self.install_dir)
                logger.debug(f"[{'] ['.join(self.yamlpath)}] Replace {self.install_dir} with backup file {files}")

            # delete empty dir
            shutil.rmtree(self.install_dir.joinpath(cwd.parts[0]))
            logger.debug(f"[{'] ['.join(self.yamlpath)}] Delete old dir {self.install_dir.joinpath(cwd.parts[0])}")

            # delete new and past old excluded file
            for file in [file for file in self.exclude_files if
                         self.install_dir.joinpath(f"{Path(file).name}.bak").exists()]:
                newfile = self.install_dir.joinpath(file)
                newfile.unlink()
                logger.debug(f"[{'] ['.join(self.yamlpath)}] Delete old file {newfile}")
                shutil.move(self.install_dir.joinpath(f"{Path(file).name}.bak"), newfile)
                logger.debug(
                    f"[{'] ['.join(self.yamlpath)}] Replace {newfile} with backup file {self.install_dir.joinpath(f'{Path(file).name}.bak')}")

        # if updating northstar move backup mods back to mod folder
        if self.repository == "R2Northstar/Northstar":
            baklst = []
            for mod in cwd.joinpath(".bakmods").iterdir():
                baklst.append(cwd.joinpath(mod))

            for mod in baklst:
                shutil.move(cwd.joinpath(mod), cwd.joinpath("R2Northstar\mods"))

            cwd.joinpath(".bakmods").rmdir()

    def run(self):
        logger.info(f"[{'] ['.join(self.yamlpath)}] Searching for new releases...")
        if self.ignore_updates and not updateAllIgnoreManager and not updateClient:
            logger.info(f"[{'] ['.join(self.yamlpath)}] Search stopped for new releases  for {self.blockname}")
            return

        tag = ""
        try:
            if self.is_github:
                release = self.release()
                url = self.asset(release)
                t = release.published_at
                tag = release.tag_name

            else:
                t = datetime.fromisoformat(
                    str(requests.get(str(self.repo)).json()["latest"]["date_created"]).split(".")[0])
                tag = str(requests.get(str(self.repo)).json()["latest"]["version_number"])
                if updateAllIgnoreManager \
                        or updateServers \
                        or updateClient \
                        or not self.file.exists() \
                        or t > self.last_update:
                    url = requests.get(str(self.repo)).json()["latest"]["download_url"]
                else:
                    raise NoValidRelease("no new Release found")

            with tempfile.NamedTemporaryFile() as download_file:
                logger.info(f"[{'] ['.join(self.yamlpath)}] Downloading: {url}")
                download(url, download_file)
                release_zip = zipfile.ZipFile(download_file)
                self.extract(release_zip)
                self.last_update = t
                logger.info(f"[{'] ['.join(self.yamlpath)}] Installed successfully update for {self.blockname}")

        except NoValidRelease:
            logger.info(f"[{'] ['.join(self.yamlpath)}] Latest Version already installed for {self.blockname}")
            return
        except NoValidAsset:
            logger.warning(
                f"[{'] ['.join(self.yamlpath)}] Possibly faulty release for {self.blockname} published Version {tag} has no valit assets")
            return


# ====
# main
# ====
def main():
    # prints help
    if showHelp:
        printhelp()
        exit(0)

    if not noUpdates:
        # check for updates/ manages updates / installs updates
        try:
            # restart updater when encountering a GitHub rate error
            while not updater():
                logger.info(f"Waiting and re-trying to update in 60s...")
                time.sleep(60)

        except PermissionError as permission:
            logger.error(f"Server ({Path(permission.filename).parent.name}) is still running")
            exit(1)
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
    for section in [s for s in config.keys() if s not in ["Global", "Launcher"]]:
        yamlpath = [section]
        try:
            if section == "Manager":
                if not updateAllIgnoreManager and not onlyCheckServers and not updateServers:
                    if config[section].get() is None:
                        raise SectionHasNoSubSections(yamlpath)
                    ManagerUpdater(yamlpath).run()

            elif section == "Mods":
                if not onlyCheckServers and not updateServers:
                    if config[section].get() is None:
                        raise SectionHasNoSubSections(yamlpath)
                    for mod in config[section]:
                        yamlpath = [section, mod]
                        ModUpdater(yamlpath).run()

                    section = "Launcher"
                    logger.info(f"[Config] Applying configurations")
                    logger.debug(f"[Config] [ns_startup_args.txt] Applying config...")
                    if config[section].get() is None:
                        raise SectionHasNoSubSections(yamlpath)

                    replace_str = ""
                    config_list = str(config[section]["arguments"].get(confuse.Optional(str, default=""))).strip() + " "
                    c_dict = {}
                    config_value = ""
                    for c in re.split('([-+])', config_list)[1:]:
                        if c == "+" or c == "-":
                            config_value = c
                            continue
                        config_value += c
                        config_value.strip()
                        split = config_value.split(" ")
                        c_dict[split[0]] = split[1] if len(split[1:-1]) == 1 else " ".join(split[1:-1])

                    with open("ns_startup_args.txt", 'r') as replace:
                        while line := replace.readline():
                            line = line.strip()
                            config_value = ""
                            for c in re.split('([-+])', line)[1:]:
                                if c == "+" or c == "-":
                                    config_value = c
                                    continue
                                config_value += c
                                config_value.strip()
                                split = config_value.split(" ")
                                key = split[0]
                                va = split[1] if len(split[1:-1]) == 1 else " ".join(split[1:-1])

                                if key in c_dict.keys():
                                    continue
                                replace_str += f"{key} {va} "

                    for k, v in c_dict.items():
                        replace_str += f"{k} {v} "
                    replace_str = replace_str.replace("  ", " ").strip()

                    # write new config to file
                    with open("ns_startup_args.txt", "w") as replace:
                        replace.write(replace_str)

            elif section == "Servers":
                if (not onlyCheckClient and not updateClient) or updateServers:
                    if config[section].get() is None:
                        raise SectionHasNoSubSections(yamlpath)
                    if not updateServers:
                        if not config[section]["enabled"].get(
                                confuse.Optional(bool, default=True)) and not updateAllIgnoreManager:
                            logger.info(f"[{'] ['.join(yamlpath)}] Searvers are disabled")
                            continue
                    for server in [s for s in config[section] if s not in ["enabled"]]:
                        yamlpath = [section, server]
                        if config[section].get() is None:
                            raise SectionHasNoSubSections(yamlpath)
                        if not updateServers and not updateAllIgnoreManager:
                            if not config[section][server]["enabled"].get(confuse.Optional(bool, default=True)):
                                logger.info(f"[{'] ['.join(yamlpath)}] Server: {server} is disabled")
                                continue
                        server_path = Path(
                            config[section][server]["dir"].get(confuse.Optional(str, default=f"./Servers/{server}")))
                        if not server_path.joinpath("Titanfall2.exe").exists():
                            logger.warning(
                                f"[{'] ['.join(yamlpath)}] Titanfall2 files invalid or don't exists at server location")
                            install_tf2(server_path)
                        if not server_path.joinpath("auto_restart.bat").exists():
                            logger.warning(
                                f"[{'] ['.join(yamlpath)}] Auto-Restart script not found at server location")
                            with open(server_path.joinpath("auto_restart.bat"), "w") as auto_restart:
                                auto_restart.write('''@echo off 
echo Starting %1 %2
goto restart

:restart
start /b /wait %1 %2
echo Server exited with code: %errorlevel%
@if %errorlevel% == 0 (goto exit) else (echo Re-Starting Server %1 && goto restart)

:exit
''')
                                logger.info(
                                    f"[{'] ['.join(yamlpath)}] Successfully created auto_restart.bat at server location")
                        for con in [s for s in config[section][server] if s not in ["enabled"]]:
                            if con == "Mods":
                                for mod in config[section][server][con]:
                                    yamlpath = [section, server, con, mod]
                                    ModUpdater(yamlpath).run()
                            elif con == "Config":
                                logger.info(f"[{'] ['.join(yamlpath)}] Applying configurations")
                                for file in config[section][server][con]:
                                    yamlpath = [section, server, con, file]
                                    logger.debug(f"[{'] ['.join(yamlpath)}] Applying config...")
                                    if file == "ns_startup_args_dedi.txt":
                                        x = Path(server_path / file)

                                        replace_str = ""
                                        config_list = str(config[section][server][con][file].get()).strip() + " "
                                        c_dict = {}
                                        config_value = ""
                                        for c in re.split('([-+])', config_list)[1:]:
                                            if c == "+" or c == "-":
                                                config_value = c
                                                continue
                                            config_value += c
                                            config_value.strip()
                                            split = config_value.split(" ")
                                            c_dict[split[0]] = split[1] if len(split[1:-1]) == 1 else " ".join(
                                                split[1:-1])

                                        with open(x, 'r') as replace:
                                            while line := replace.readline():
                                                line = line.strip()
                                                config_value = ""
                                                for c in re.split('([-+])', line)[1:]:
                                                    if c == "+" or c == "-":
                                                        config_value = c
                                                        continue
                                                    config_value += c
                                                    config_value.strip()
                                                    split = config_value.split(" ")
                                                    key = split[0]
                                                    va = split[1] if len(split[1:-1]) == 1 else " ".join(split[1:-1])

                                                    if key in c_dict.keys():
                                                        continue
                                                    replace_str += f"{key} {va} "

                                        for k, v in c_dict.items():
                                            replace_str += f" {k} {v}"
                                        replace_str = replace_str.replace("  ", " ").strip()

                                        # write new config to file
                                        with open(x, "w") as replace:
                                            replace.write(replace_str)

                                    elif file == "mod.json":
                                        for file_section in config[section][server][con][file]:
                                            yamlpath = [section, server, con, file, file_section]
                                            if file_section == "ConVars":

                                                x = Path(
                                                    server_path / "R2Northstar/mods/Northstar.CustomServers" / file)

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
                                                logger.error(f"[{'] ['.join(yamlpath)}] Unknown section {file_section}")

                                    elif file == "autoexec_ns_server.cfg":
                                        x = Path(
                                            server_path / "R2Northstar/mods/Northstar.CustomServers/mod/cfg" / file)

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

                            else:
                                logger.warning(f"[{'] ['.join(yamlpath)}] Unknown Field {con}")

            else:
                logger.warning(f"[{'] ['.join(yamlpath)}] Unknown Section {section}")

        except SectionHasNoSubSections:
            logger.warning(
                f"[{'] ['.join(yamlpath)}] Skipping Section, config is invalid or is missing subsections")
            return True

        except (RateLimitExceededException, ConnectionError):
            logger.warning(f"[{'] ['.join(yamlpath)}] Rate limit exceeded")
            if len(git_token) > 0:
                logger.info(
                    f"[{'] ['.join(yamlpath)}] Available GitHub requests left {g.rate_limiting[0]}/{g.rate_limiting[1]}")
            if "y" != input("Wait and try update again in 60sec? (y/n) "):
                break
            return False

        except FileNotInZip:
            logger.warning(f"[{'] ['.join(yamlpath)}] Zip file for doesn't contain expected files")
            return True
        except FileNotFoundError as file_not_found:
            logger.error(f"[{'] ['.join(yamlpath)}] File ({Path(file_not_found.filename).name}) does not exist")
            exit(1)
    logger.info(f"Successfully checkt all Mods and Servers")
    return True


# =============================
# launches the defined launcher
# =============================
def launcher():
    script = f'"{config["Launcher"]["filename"].get()}"{(" " + " ".join(sysargs[1::])) if len(sysargs) > 1 else ""}{" -" + loglevel[0] if len(loglevel) > 0 else ""}'
    pre_launch_origin()
    try:
        logger.info(f"[Launcher] Launching {script}")
        subprocess.Popen(script, cwd=str(Path.cwd()), shell=True)
    except FileNotFoundError:
        logger.error(f"[Launcher] Could not find given file {script}")
        exit(1)


# ==================
# prelaunches origin
# ==================
def pre_launch_origin():
    script = "C:/Program Files (x86)/Origin/Origin.exe"
    try:
        if "Origin.exe" not in (p.name() for p in psutil.process_iter()):
            logger.info(f"[Launcher] Launching Origin and waiting 10sec...")
            subprocess.Popen(script, cwd=str(Path.cwd()), shell=True)
            time.sleep(10)
            logger.info(f"[Launcher] Launched  Origin succesfull")

    except FileNotFoundError:
        logger.error(f"[Launcher] Could not find given file {script}")
        exit(1)


# ============================
# launches all enabled servers
# ============================
def launchservers():
    scripts = []

    if not config["Servers"]["enabled"].get(confuse.Optional(bool, default=True)):
        logger.info(f"[Launcher] All servers are disabled")
        return
    for server in config["Servers"]:
        if server != "enabled":
            if not config["Servers"][server]["enabled"].get(confuse.Optional(bool, default=True)):
                logger.info(f"[Launcher] Server: {server} is disabled")
                continue
            else:
                server_dir = config["Servers"][server]["dir"].get(confuse.Optional(str, f"Servers/{server}"))
                scripts.append(
                    f'start cmd.exe /c "cd /d {server_dir} && auto_restart.bat NorthstarLauncher.exe -dedicated"')

    if len(scripts) == 0:
        logger.warning(f"[Launcher] No enabled Servers found")
        return

    # Add a pause in between launching servers
    logger.info("[Launcher] Launching servers in an intervall of 10 seconds")
    scripts = f" && timeout /t 10 /nobreak >nul 2>&1 && ".join(scripts)
    subprocess.Popen(scripts, cwd=str(Path.cwd()), shell=True)


main()
# ============
# write config
# ============
with open("manager_config.yaml", "w+") as f:
    logger.debug(f"Writing config to {f.name}")
    yaml.dump(conf_comments, f)
