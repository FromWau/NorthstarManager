py -m nuitka --standalone --onefile --enable-plugin=anti-bloat --include-module=tqdm --windows-icon-from-ico=ns_icon_pink.ico NorthstarUpdater.py
Remove-Item .\NorthstarUpdater.onefile-build\,.\NorthstarUpdater.dist\,.\NorthstarUpdater.build\ -Recurse