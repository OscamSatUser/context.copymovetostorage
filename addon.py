import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import sys
import os
import threading
import json

__addon__ = xbmcaddon.Addon()

def background_copy(src, dest, filename):
    """
    Uses native C++ copy for stability (no codec errors) 
    and a monitor thread for real-time progress.
    """
    p_dialog = xbmcgui.DialogProgressBG()
    p_dialog.create("Transferring", f"Waiting for SMB: {filename}")
    
    try:
        # 1. Get total size from source using Stat (doesn't read file data)
        stat_src = xbmcvfs.Stat(src)
        total_size = stat_src.st_size()
        
        # 2. Start native copy in its own thread
        copy_thread = threading.Thread(target=xbmcvfs.copy, args=(src, dest))
        copy_thread.start()
        
        # 3. Monitor the destination file size
        while copy_thread.is_alive():
            if xbmcvfs.exists(dest):
                stat_dest = xbmcvfs.Stat(dest)
                current_size = stat_dest.st_size()
                
                if total_size > 0:
                    percent = int((current_size / total_size) * 100)
                    p_dialog.update(max(1, percent), message=f"{percent}% - {filename}")
            
            xbmc.sleep(1000) # Poll every second

        # 4. Finalize
        copy_thread.join() # Ensure the thread is finished
        
        if xbmcvfs.exists(dest):
            stat_dest = xbmcvfs.Stat(dest)
            size_dest = stat_dest.st_size()
            
            # Verify file integrity
            if total_size == size_dest and size_dest > 0:
                dest_dir = os.path.dirname(dest)
                xbmc.executebuiltin(f'UpdateLibrary(video, "{dest_dir}")')
                
                if xbmcgui.Dialog().yesno("Transfer Complete", f"Successfully copied.\n{filename}\nDelete source file?"):
                    if not xbmcvfs.delete(src):
                        xbmcgui.Dialog().notification("Failed!", "Source was NOT deleted!")
            else:
                # Fixed variable name from current_size to total_size for logging
                xbmc.log(f"COPY_ERROR: Size mismatch! Source: {total_size} Dest: {size_dest}", xbmc.LOGERROR)
                xbmcgui.Dialog().notification("Error", "Transfer corrupted.")
        else:
            xbmcgui.Dialog().notification("Error", "Destination file missing.")

    except Exception as e:
        xbmc.log(f"MONITOR_ERROR: {repr(e)}", xbmc.LOGERROR)
    finally:
        p_dialog.close()

def main():
    try:
        li_path = sys.listitem.getPath()
        if not li_path: return

        dest_folder = xbmcgui.Dialog().browseSingle(3, "Select Destination", "files")
        if not dest_folder: return

        filename = os.path.basename(li_path.rstrip('/'))
        if not filename or "://" in filename:
            filename = sys.listitem.getLabel() or "video_file"
            
        dest_path = os.path.join(dest_folder, filename)

        t = threading.Thread(target=background_copy, args=(li_path, dest_path, filename))
        t.daemon = True
        t.start()

    except Exception as e:
        xbmc.log(f"MAIN_ERROR: {repr(e)}", xbmc.LOGERROR)

if __name__ == '__main__':
    main()
