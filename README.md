# Joplin Revisions Cleanup

I don't know if this is really necessary, but this little python script cleans up "orphaned" revisions from the remote folder.

Joplin seems to leave revisions on the remote sync folder, even though they don't exist locally anymore. This leads them to pile up. See [this forum post](https://discourse.joplinapp.org/t/joplin-creates-a-lot-of-remote-items/12621).

So, I adapted [p6ril's script](https://github.com/p6ril/joplinRevisionsCleanUp) to my needs. Should work nicely on Windows now. Maybe it could be useful to you.

## Usage
First, download the script.

(e.g. via PowerShell)
```ps
iwr -Uri "https://raw.githubusercontent.com/FelisDiligens/joplin-revisions-cleanup/master/revisions-cleanup.py" -OutFile "$env:UserProfile\Downloads\revisions-cleanup.py"
```

Then open `revisions-cleanup.py` in a text editor and edit the variables to point to the correct paths.

- `DATABASE_DIR` ⇒ Should point to where the database is stored. Leave as is if you haven't changed that.  
- `JOPLIN_DIR` ⇒ Should point to your locally synced remote folder. In my case, it's stored on OneDrive.  
- `DO_BACKUP = True/False` ⇒ Change, depending on whether you want to create a backup before deleting any files.

> **IMPORTANT**: Please always make a backup of your files before running random scripts you download from the internet!

Now close Joplin and run the python script. Make sure that you have installed [Python 3](https://www.microsoft.com/store/productId/9PJPW5LDXLZ5)!  
```ps
python.exe ".\revisions-cleanup.py"
```

That should be it! :)

## Recommended
- [joplin-vacuum by jerrylususu](https://github.com/jerrylususu/joplin-vacuum) to remove orphaned attachments.