$s=Get-Date
py -m pip install --upgrade pip
py -m pip install confuse ruamel.yaml psutil requests tqdm pygithub nuitka zstandard
py -m nuitka --standalone --onefile --python-flag=-O --clang --include-module=tqdm,confuse,requests --follow-imports --assume-yes-for-downloads --windows-icon-from-ico=ns_icon_pink.ico NorthstarManager.py
$e=Get-Date; Write-Host "Compiling NorthstarManager.exe took "($e - $s).TotalSeconds" seconds"
