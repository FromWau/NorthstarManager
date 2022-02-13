python -m pip install --upgrade pip
python -m pip install tqdm confuse requests pygithub nuitka
<<<<<<< HEAD
python -m nuitka --standalone --onefile --python-flag=-O --enable-plugin=anti-bloat --clang --include-module=tqdm,confuse,requests --follow-imports --assume-yes-for-downloads --windows-icon-from-ico=ns_icon_pink.ico NorthstarManager.py
=======
python -m nuitka --standalone --onefile --python-flag=-O --enable-plugin=anti-bloat --clang --include-module=tqdm,confuse,requests --follow-imports --assume-yes-for-downloads --windows-icon-from-ico=ns_icon_pink.ico NorthstarManager.py
>>>>>>> 860172d5d7d139c815c9966f291099ec198c894b
