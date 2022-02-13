$s=Get-Date 
python -m pip install --upgrade pip 
python -m pip install tqdm confuse requests pygithub pyaml nuitka
python -m nuitka --standalone --onefile --python-flag=-O --enable-plugin=anti-bloat --clang --include-module=tqdm,confuse,requests --follow-imports --assume-yes-for-downloads --windows-icon-from-ico=ns_icon_pink.ico NorthstarManager.py
$e=Get-Date; Write-Host "Compiling NorthstarManager.exe took "($e - $s).TotalSeconds" seconds"