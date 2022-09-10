import tarfile
from pathlib import Path
import os
import os.path
import sqlite3
import sys
import subprocess
import re

#
# VARIABLES
#

DRY_RUN         = True

USER_HOME       = str(Path.home()) # Windows: %USERPROFILE%, Linux: ~
ONEDRIVE_DIR    = os.environ['ONEDRIVE'] # Windows has an environment variable: %ONEDRIVE%
#ONEDRIVE_DIR    = "/path/to/your/OneDrive/" # on Linux
DATABASE_DIR    = os.path.join(USER_HOME, ".config", "joplin-desktop") # Windows: %USERPROFILE%\.config\joplin-desktop, Linux: ~/.config/joplin-desktop
#DATABASE_DIR    = os.path.join(USER_HOME, "snap/joplin-desktop/current/.config/joplin-desktop") # Linux (Snap): ~/snap/joplin-desktop/current/.config/joplin-desktop/
JOPLIN_DIR      = os.path.join(ONEDRIVE_DIR, "Anwendungen", "Joplin") # local sync directory of Joplin's remote folder
JEX_PATH        = os.path.join(USER_HOME, "Downloads", "06.09.2022.jex")
DATABASE_NAME   = "database.sqlite"
JOPLIN_DB       = os.path.join(DATABASE_DIR, DATABASE_NAME)
JOPLIN_ID_LEN = 32

#
# FUNCTIONS
#

def is_joplin_running():
    if sys.platform.startswith('win'):
        return b"Joplin.exe" in subprocess.check_output('tasklist', shell=True)
    elif sys.platform.startswith('linux'):
        # https://stackoverflow.com/a/4139017
        try:
            ps     = subprocess.Popen("ps -eaf | grep joplin-desktop", shell=True, stdout=subprocess.PIPE)
            output = ps.stdout.read().decode("utf-8")
            ps.stdout.close()
            ps.wait()
            return re.search('/joplin-desktop/', output) is not None
        except:
            return False
    return False


def read_jex_ids():
    with tarfile.open(JEX_PATH, "r") as f:
        files = f.getmembers()
    
    ids = [f.name[:JOPLIN_ID_LEN] for f in files if not f.name.startswith("resources/")]

    return set(ids)


def get_ids_from_db():
    if os.path.isdir(DATABASE_DIR):
        conn = sqlite3.connect(JOPLIN_DB)
        c = conn.cursor()
        c.execute("select id from tags")
        # fetchall() returns a list of result tuples (not a list of id values as strings)
        tags = map(lambda i: i[0], c.fetchall())
        c.execute("select id from note_tags")
        note_tags = map(lambda i: i[0], c.fetchall())
        conn.close()
        return set(list(tags) + list(note_tags))
    else:
        print("ERROR: Joplin's database not found, aborting!")
        sys.exit(1)


def reconcile():
    # check https://www.freecodecamp.org/news/python-sets-detailed-visual-introduction/
    tag_ids = get_ids_from_db()
    jex_ids = read_jex_ids()
    unused_ids = list(tag_ids - jex_ids)

    if len(unused_ids) > 0:
        print("Number of unused Tags and NoteTags found: " + str(len(unused_ids)))
        if DRY_RUN:
            for item in unused_ids:
                print("    - " + item + ".md")
        else:
            print("Deleting ...")
            for item in unused_ids:
                path = os.path.join(JOPLIN_DIR, item + ".md")
                print("    - " + item + ".md")
                os.remove(path)
    else:
        print("No unused Tags or NoteTags found.")


if __name__ == "__main__":
    print("""Joplin Tags and NoteTags Cleanup
--------------------------------""")
    if is_joplin_running():
        print("ERROR: Please make sure to close Joplin! (File → Quit)")
        sys.exit(-1)

    if DRY_RUN:
        print("Dry run: Nothing will be deleted.")

    reconcile()

    print("Done.")