python -m pip install --upgrade pip
python -m pip install tqdm confuse requests pygithub nuitka

python -m nuitka --standalone --onefile --python-flag=-O --enable-plugin=anti-bloat --clang --include-module=tqdm,confuse,requests --follow-imports --assume-yes-for-downloads --windows-icon-from-ico=ns_icon_pink.ico NorthstarManager.py

Remove-Item .\NorthstarManager.onefile-build\,.\NorthstarManager.dist\,.\NorthstarManager.build\ -Recurse
