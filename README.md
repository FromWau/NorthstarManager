# NorthstarManager
... is a CLI based mod-manager/ auto updater tool for Titanfall2 +Northstar

## How to install
1. Download the NorthstarManager.exe from the [latest release page](https://github.com/FromWau/NorthstarManager/releases/latest/download/NorthstarManager.exe)
2. Put the NorthstarManager.exe into your Titanfall2 folder. (folder which includes the Titanfall2.exe)
3. Run NorthstarManager.exe and have fun

## Configuration
Configuration happens in the 'updater_config.ini'. The config file will be generated at launch.

| Flag | Expected Value | Description |
| --- | --- | --- |
| [Mod_Titel] | Name of the mod in square brackets | Defines a mod section. |
| repository | Owner/RepositoryName (eg. FromWau/NorthstarManager) | Declares the repository of the mod. |
| github_token | `optional` Github Token <br> `default` no token | Sets the Token for requests to github. A token is not mandatory but it increases the github rate limit substantially. [Get Github Token](https://github.com/settings/tokens) |
| last_update | Timestamp with format yyyy-mm-ddThh:mm:ss (eg. 2022-02-07T13:07:29) | Defines the Timestamp when repository was updated. |
| ignore_updates | `optional` true / false <br> `default` false | If true the mod with the set flag will not receive updates. |
| ignore_prerelease | `optional` true / false <br> `default` false | If true will ignore releases marked as prerelease. |
| file | `optional` filename <br> `default` mod.json | Sets the filename of the mod. Manager will render mod as corrupted if the file doesn't exist. |
| install_dir | `optional` Path to install directory of mod. (eg. .) <br> `default` ./R2Manager/mods | Defines the install location of the mod. |
| exclude_files | `optional` ​"ns_startup_args.txt|ns_startup_args_dedi.txt) <br> `default` 





## Launcher Arguments
NorthstarManager.exe can be launched with following flags:

| Launch Arguments | Description |
| --- | --- |
| -help | prints the help section for NorthstarManager |
| -update-everything | updates all repos defined in the 'config_updater.ini' to the latest release regardless of maybe being the latest release, ignoring flags: 'ignore_updates' |​
| -onlyUpdate | only runs the updater without launching the defined launcher in the 'config_updater.ini'​ |
| -onlyLaunch | only launches the defined launcher in the 'config_updater.ini', without updating​ |
| -dedicated | runs the laucnher as dedicated server​ |
