NorthstarManager
====
is a CLI based updater tool for [Northstar](https://github.com/R2Northstar/Northstar) and for custom Northstar mods published on Github. The Manager can be configured via the 'updater_config.ini' or/and via Launch arguments. <br>

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
| token | `optional` Github Token <br> `default` no token | Sets the Token for requests to github. A token is not mandatory but it increases the github rate limit substantially. [Get Github Token](https://github.com/settings/tokens) |

## Launcher
| Flag | Expected Value | Description |
| --- | --- | --- |
| arguments | launcher arguments | Expects TF2 launcher arguments or the arguments from the [launcher arguments section](#launcher-arguments)). Multiple arguments can be separated by space. |
| filename | Path to file | Path to NorthstarLauncher.exe |

## Manager
| Flag | Expected Value | Description |
| --- | --- | --- |
| repository | Owner/RepositoryName (eg. FromWau/NorthstarManager) | Declares the repository of the mod. |
| last_update | Timestamp with format yyyy-mm-ddThh:mm:ss (eg. 2022-02-07T13:07:29) | Defines the Timestamp when repository was updated. |
| ignore_updates | `optional` true / false <br> `default` false | If true the mod with the set flag will not receive updates. |
| ignore_prerelease | `optional` true / false <br> `default` false | If true will ignore releases marked as prerelease. |
| file | `optional` filename <br> `default` mod.json | Sets the filename of the mod. Manager will render mod as corrupted if the file doesn't exist. |
| install_dir | `optional` Path to install directory of mod. (eg. .) <br> `default` ./R2Manager/mods | Defines the install location of the mod. |
| exclude_files | `optional` Filename (eg. ns_startup_args.txt\|ns_startup_args_dedi.txt) <br> `default` no files | Files to be excluded from replacing when installing the new version of a mod. Files will be separated by \|. |

# Launcher Arguments
NorthstarManager.exe can be launched with following flags:

| Launch Arguments | Description |
| --- | --- |
| -help | Prints the help section for NorthstarManager |
| -updateAll | Updates all repos defined in the 'config_updater.ini' to the latest release regardless of the latest release maybe being already installed, ignoring flags: 'ignore_updates' |
| -updateAllIgnoreManager | Updates all repos defined in the 'config_updater.ini', except the Manager section, to the latest release regardless of the latest release maybe being already installed, ignoring flags: 'ignore_updates' |
| -onlyUpdate | Only runs the updater without launching the defined launcher in the 'manager_conf.ymal' |
| -onlyLaunch | Only launches the defined file from the Launcher section, without updating the repos |

