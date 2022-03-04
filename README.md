NorthstarManager
====
is a CLI based updater tool for [Northstar](https://github.com/R2Northstar/Northstar) and for custom Northstar mods published on Github or [northstar.thunderstore.io](https://northstar.thunderstore.io/). The Manager can be configured via the 'manager_config.yaml' or/and via Launch arguments and used to setup dedicated servers. <br>

# Contents
- [Features](#features)
- [How to install](#how-to-install)
- [Configuration](#configuration)
  - [Global](#global)
  - [Launcher](#launcher)
  - [Manager](#manager)
  - [Mods](#mods)
  - [Servers](#servers)
- [Launcher Arguments](#launcher-arguments)
- [Compile it yourself](#compile-it-yourself)

# Features
- Auto-Install of Northstar and mods
- Auto-Updater for Northstar, mods and itself
- Auto-Install, Auto-Setup and Auto-Configuration of dedicated servers

The [example_manager_config.yaml](https://github.com/FromWau/NorthstarManager/blob/main/example_manager_config.yaml) describes how to configure the manager/ mods/ servers. A list of example dedicated servers is also included which can just be copy pasted to your config file.

# How to install
1. [Download the latest NorthstarManager.exe](https://github.com/FromWau/NorthstarManager/releases/latest/download/NorthstarManager.exe) or download another Version from the [release page](https://github.com/FromWau/NorthstarManager/releases).
2. Put the NorthstarManager.exe into your Titanfall2 folder. (folder which includes the Titanfall2.exe)
3. Run NorthstarManager.exe

# Configuration
Configuration happens in the 'manager_conf.ymal'. The config file will be generated at launch. <br>
`optional` flags are not necessarily for a valid configuration. If not present the value will be the `default` value.<br>
Configuration will be separated by following sections:

## Global
Settings that persist for all other sections.
| Flag | Expected Value | Description |
| --- | --- | --- |
| github_token | `optional` Github Token <br> `default` no token | Sets the Token for requests to github. A token is not mandatory but it increases the github rate limit substantially. [Get Github Token](https://github.com/settings/tokens) |
| log_level | `optional` Log Level <br> (eg. INFO) | Sets the loggong level for the manager. Can be set to DEBUG, INFO, WARNING or ERROR.

## Launcher
| Flag | Expected Value | Description |
| --- | --- | --- |
| filename | Path to file | Path to NorthstarLauncher.exe or Titandfall2.exe (if you want to play vanilla Titanfall) |
| arguments | `optional` launcher arguments | Expects TF2 launcher arguments those will overrite/ expande the arguments saved in the ns_startup_args.txt. Multiple arguments can be separated by space. |

## Manager
| Flag | Expected Value | Description |
| --- | --- | --- |
| repository | Owner/RepositoryName (eg. FromWau/NorthstarManager) | Declares the repository of the manager. |
| last_update | Timestamp with format yyyy-mm-ddThh:mm:ss (eg. 2022-02-07T13:07:29) | Defines the Timestamp when the repository was updated. |
| file | `optional` NorthstarManager.exe <br> `default` mod.json | Sets the filename of the mod. |
| install_dir | `optional` Path to install directory of mod. (eg. .) <br> `default` ./R2Manager/mods | Defines the install location of the mod. |
| ignore_updates | `optional` Boolean (eg. true) <br> `default` false | Will ignore new version and keeps the installed version |
| ignore_prerelease | `optional` Boolean (eg. true) <br> `default` false | Will ignore pre releases when searching for new realeses of the repo |

## Mods
List of mod entries eg.:<br>
Mods:<br>
&nbsp;&nbsp;&nbsp;Mod1:<br> 
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;...<br>
&nbsp;&nbsp;&nbsp;Mod2:<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;...<br>

| Flag | Expected Value | Description |
| --- | --- | --- |
| repository | Owner/RepositoryName (eg. R2Northstar/Northstar) | Declares the repository of the mod. |
| last_update | Timestamp with format yyyy-mm-ddThh:mm:ss (eg. 2022-02-07T13:07:29) | Defines the Timestamp when the repository was updated. |
| file | `optional` NorthstarLauncher.exe <br> `default` mod.json | Sets the filename of the mod. |
| install_dir | `optional` Path to install directory of mod. (eg. .) <br> `default` ./R2Manager/mods | Defines the install location of the mod. |
| exclude_files | `optional` Filename (eg.<br>exclude_files:<br> - ns_startup_args.txt<br> - ns_startup_args_dedi.txt) <br> `default` no files | Files to be excluded from replacing when installing the new version of a mod. Files need to be listed as list. |
| ignore_updates | `optional` Boolean (eg. true) <br> `default` false | Will ignore new version and keeps the installed version |
| ignore_prerelease | `optional` Boolean (eg. true) <br> `default` false | Will ignore pre releases when searching for new realeses of the repo |

## Servers
List of server entries eg.:<br>
Servers:<br>
&nbsp;&nbsp;&nbsp;Server1:<br> 
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Mods:](#mods)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;...<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[Config:](#config)<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;...<br>
&nbsp;&nbsp;&nbsp;Server2:<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;...<br>

The Server section is divided by Mods and the config section.<br>
Additionaly Servers and indiviual servers like Server1, Server2, etc. can be disabled by enabled: false

### Mods
The mods for the servers are the same way configured like [client mods](#mods).

### Config
The config is spaced out between three files (mod configs can also be added to one of those files): 
- ns_startup_args_dedi.txt<br>
Contains the startup arguments and is the equivalent to the Launcher - arguments for servers. <br>
Expects TF2 servers launcher arguments those will overrite/ expande the arguments saved in the ns_startup_args_dedi.txt file. Multiple arguments can be separated by space. Following example sets the server mode to pilot vs pilot and sets the air accelaration to 9,000: `+mp_gamemode ps +setplaylistvaroverrides "custom_air_accel_pilot 9000"`<br>
Link to the Wiki: https://r2northstar.gitbook.io/r2northstar-wiki/hosting-a-server-with-northstar/dedicated-server#startup-arguments

- mod.json<br>
Contains a list of ConVars of the server.<br>
ConVars:<br>
&nbsp;&nbsp;&nbsp; key: value<br>
Link to the Wiki: https://r2northstar.gitbook.io/r2northstar-wiki/hosting-a-server-with-northstar/dedicated-server#convars

- autoexec_ns_server.cfg<br>
Contains the basic configuration list for the server.<br>
key: value<br>
Link to the Wiki: https://r2northstar.gitbook.io/r2northstar-wiki/hosting-a-server-with-northstar/basic-listen-server#server-configuration

# Launcher Arguments
NorthstarManager.exe can be launched with following flags:

| Launch Arguments | Description |
| --- | --- |
| -help | Prints the help section for NorthstarManager. |
| -updateAll | Force updates all repos defined in the 'manager_config.yaml' to the latest release regardless of the latest release maybe being already installed, ignoring config flags: 'ignore_updates'. |
| -updateAllIgnoreManager | Force updates all repos defined in the 'manager_config.yaml', except the Manager section, to the latest release regardless of the latest release maybe being already installed, ignoring config flags: 'ignore_updates'. |
| -updateServers | Force updates all repos defined in the 'manager_config.yaml' under the Servers section. |
| -updateClient | Force updates all repos defined in the 'manager_config.yaml' under the Manager and Mods section. |
| -onlyCheckServers | Looks for updates only for repos defined in the 'manager_config.yaml' under section Servers. |
| -onlyCheckClient | Looks for updates only for repos defined in the 'manager_config.yaml' under section Manager and Mods. |
| -noUpdate | Only launches the defined file from the Launcher section, without checking for updates. |
| -noLaunch | Checks for updates for all repos defined in the 'manager_config.yaml' without launching the defined launcher in the 'manager_conf.ymal'. |
| -launchServers | Launches all enabled servers from the Servers section in the 'manager_config.yaml' file. |

# Compile it yourself
Compiliation from py to exe is done via nuitka, but you could also use pyinstaller or something else.<br>
The compile.ps1 runs a pip install for the required python modules and starts the nuitka compilation. The scripts takes a 1950X about ~255 seconds.    
