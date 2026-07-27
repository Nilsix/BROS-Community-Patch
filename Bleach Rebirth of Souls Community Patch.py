from tkinter import * 
from tkinter import messagebox
from tkinter import filedialog
from tkinter import ttk
import json
import shutil
import os
import subprocess   
import platform
try :
    import ctypes
except:
    pass
try:
    import winsound
except:
    pass
import sys
import webbrowser
from pathlib import Path

try:
    import requests 
except:
    pass
try:
    import hashlib
except:
    pass

try: 
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    print("Checking for updates, please wait")

    reworks = ["OFF"]

    # ── Version info ─────────────────────────────────────────────────────────
    # PATCH_VERSION: bump this by hand whenever you want the displayed version
    # number to change (ex: "1.0" -> "1.1"). This is NOT automatic on purpose.
    #PATCH_VERSION = "1.0"

    def get_snapshot():
        """Returns the short git commit hash currently checked out.
        This updates automatically every time the launcher does a 'git pull',
        so it always reflects whatever was last pushed to GitHub."""
        try:
            result = subprocess.run(
                ["git", "-C", BASE_DIR, "rev-parse", "--short", "HEAD"],
                check=True, capture_output=True, text=True
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"
    
    def get_latest():
        """Short commit hash of origin/main (the newest pushed build). Does a
        quiet fetch so it is accurate even for DevToken users who skip the
        reset. Returns 'unknown' offline."""
        try:
            subprocess.run(["git","-C",BASE_DIR,"fetch","--quiet"],
                           capture_output=True, text=True, timeout=20)
            r = subprocess.run(["git","-C",BASE_DIR,"rev-parse","--short","origin/main"],
                               check=True, capture_output=True, text=True)
            return r.stdout.strip()
        except Exception:
            return "unknown"

    def compute_match_code(build, gameVersion):
        """The online room/match code for a given build + version. Must stay
        byte-identical to setup_matchmaking() so the launcher shows exactly what
        the loader writes to patch_ranked.txt."""
        import zlib
        seed = f"{build}|{gameVersion}"
        return 100000 + (zlib.crc32(seed.encode("utf-8")) % 800000)

    def read_loaded_code():
        """The match code the loader actually installed for THIS player, read
        from the last 'match code <n> loaded' line of patch_ranked.log next to
        the game exe. Lets a player confirm their room code installed right."""
        try:
            import re
            p = os.path.join(game_path, "patch_ranked.log")
            last = None
            with open(p, encoding="utf-8", errors="replace") as f:
                for line in f:
                    m = re.search(r"match code (\d+) loaded", line)
                    if m:
                        last = m.group(1)
            return last
        except Exception:
            return None

    def pulling_from_git():
        # Ensure git can write the deep Effect/spfx/... paths that blow past the
        # legacy 260-char Windows limit. core.longpaths makes git use \\?\
        # extended paths internally -- no admin, no registry change, no reboot.
        # A partial "Filename too long" clone then self-heals on launch: the
        # objects are already downloaded, so the reset --hard below writes the
        # missing long-path files with zero action from the user.
        subprocess.run(["git","-C",BASE_DIR,"config","core.longpaths","true"], capture_output=True, text=True)
        if os.path.exists(os.path.join(BASE_DIR,"BalanceLeadTools","DevToken.txt")) == False:
            subprocess.run(["git","-C",BASE_DIR,"fetch"], check=True, capture_output=True, text=True)
            subprocess.run(["git","-C",BASE_DIR,"reset","--hard","origin/main"], check=True, capture_output=True, text=True)
            subprocess.run(["git","-C",BASE_DIR,"clean","-fd","-e","Json"], check=True, capture_output=True, text=True)
        return subprocess.run(["git", "-C", BASE_DIR, "pull"], check=True, capture_output=True, text=True)


    try:
        result = pulling_from_git()
        output = result.stdout.strip()
        if "Already up to date." in output:
            pass
        
        #if there is an update, will relaunch the launcher so the code actually gets reset too
        else:
            pass
            #subprocess.run(os.path.join(BASE_DIR,"Bleach Rebirth of Souls Community Patch.py"),shell=True)
            #try :
                #winsound.PlaySound(None,winsound.SND_PURGE)
            #except:
                #pass
            input("A new update just dropped, press enter to close this window then reopen your launcher")
            exit()

    except Exception as e:
        try:
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 1)
        except:
            pass
        print("Git update failed :", e)
        print("Please relaunch the installer script, while installing make sure to wait for the installer window to close itself, DO NOT close it yourself please")
        a = input("Press Enter to exit ")
        exit()
    
    def refresh_launcher():
        subprocess.run(os.path.join(BASE_DIR,"Bleach Rebirth of Souls Community Patch.py"),shell=True)
        try :
            winsound.PlaySound(None,winsound.SND_PURGE)
        except:
            pass
        exit()
    
    def open_file(path):
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])
   
    template_path = os.path.join(BASE_DIR,"Json","configTemplate.json")
    config_path = os.path.join(BASE_DIR,"Json","config.json")
    admin_config_path = None

    try:
        if os.path.exists(os.path.join(BASE_DIR,"adminConfig.json")):
            admin_config_path = os.path.join(BASE_DIR,"adminConfig.json")
    except:
        admin_config_path = None
    
    if not os.path.exists(config_path):
        shutil.copy(template_path,config_path)
    else:
        with open(template_path, "r",encoding="utf-8") as f:
            data1 = json.load(f)
        with open(config_path,"r",encoding="utf-8") as f:
            data2 = json.load(f)
        if len(data1) != len(data2):
            shutil.copy(template_path,config_path)
    config_path = os.path.join(BASE_DIR,"Json","config.json")

    with open(config_path, "r") as f:
        config = json.load(f)

    admin_config = None
    
    if admin_config_path is not None:
        with open(admin_config_path, "r") as f:
            admin_config = json.load(f)
    
    
    def saveJson():
        with open(config_path,"w") as f:
            json.dump(config,f)

    VERSION_STRING = f"{get_snapshot()}"
    if admin_config_path != None:
        try:
            if VERSION_STRING != admin_config["VERSION"] : 
                admin_config["VERSION"] = VERSION_STRING
                with open(admin_config_path,"w") as f:
                    json.dump(admin_config,f)

                hash = hashlib.sha256(admin_config["HASH_VALUE"].encode()).hexdigest()
                
                if admin_config["ADMIN_ID"] == hash:
                    webhook_url = "https://discord.com/api/webhooks/1522537997751549972/AUYztUb1AS77vhsc6ERfeRYE9kNu0KLfem8HP9CGQDVe0lrkOeNarf8VlPGbrAyj-jeZ"
                    try : 
                        requests.post(webhook_url, json={"content": "Launcher latest version : " + VERSION_STRING})
                    except:
                        pass
        except:
            pass
       

    # DPI-aware BEFORE creating the window, so text renders crisp at the monitor's
    # native resolution instead of Windows bitmap-stretching it (that stretch is
    # what looked washed-out / soft).
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)   # per-monitor v2 (Win 8.1+)
    except Exception:
        try: ctypes.windll.user32.SetProcessDPIAware()   # fallback (older Windows)
        except Exception: pass

    window = Tk()
    window.withdraw()                     # stay hidden until sized to fit content
    try:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass
    window.title("Bleach Community Patch")
    try: window.iconbitmap(os.path.join(BASE_DIR,"ressources/pimplin.ico"))
    except Exception: pass
    #minimum size of the window
    window.minsize(600,400)
    # Final size is computed at the very end by fit_window(), after every widget
    # exists: the window is sized to exactly fit its content (capped to the
    # screen) and centred -- crisp at native DPI, nothing cut off, no resizing.
    bgcolor = "#4A1942"
    labelcolor = "#D9B8D4"
    window.config(background=bgcolor)
    gameMode = "DEFAULT"

    # ── Hover helpers ──────────────────────────────────────────────────────────
    HOVER_BG   = "#F5D6F0"   # light lilac highlight on mouse-over
    NORMAL_BG  = "white"

    class Tooltip:
        """Small pop-up label that appears after the mouse rests on a widget."""
        DELAY_MS = 700          # how long the cursor must stay still before appearing

        def __init__(self, widget, text):
            self.widget  = widget
            self.text    = text
            self._job    = None
            self._tip_wnd = None
            widget.bind("<Enter>",    self._schedule, add="+")
            widget.bind("<Leave>",    self._cancel,   add="+")
            widget.bind("<ButtonPress>", self._cancel, add="+")

        def _schedule(self, event=None):
            self._cancel()
            self._job = self.widget.after(self.DELAY_MS, self._show)

        def _cancel(self, event=None):
            if self._job:
                self.widget.after_cancel(self._job)
                self._job = None
            self._hide()

        def _show(self):
            if self._tip_wnd:
                return
            x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
            self._tip_wnd = tw = Toplevel(self.widget)
            tw.wm_overrideredirect(True)          # no title bar / borders
            tw.wm_geometry(f"+{x}+{y}")
            tw.attributes("-topmost", True)
            lbl = Label(
                tw, text=self.text,
                background="#FFFBCC", foreground="#222222",
                relief="solid", borderwidth=1,
                font=("Segoe UI", 10), padx=6, pady=3
            )
            lbl.pack()

        def _hide(self):
            if self._tip_wnd:
                self._tip_wnd.destroy()
                self._tip_wnd = None

    def add_hover(btn, tooltip_text=""):
        """Attach a light-up hover colour and an optional tooltip to a Button."""
        btn.bind("<Enter>", lambda e: btn.config(bg=HOVER_BG), add="+")
        btn.bind("<Leave>", lambda e: btn.config(bg=NORMAL_BG), add="+")
        if tooltip_text:
            Tooltip(btn, tooltip_text)
    # ──────────────────────────────────────────────────────────────────────────
     
    

    ressourcesPath = os.path.join(BASE_DIR,"ressources")
    launcherOstPath = os.path.join(ressourcesPath,"LauncherOst.wav")
    
    try:
        winsound.PlaySound(launcherOstPath,winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
    except:
        pass
    game_path = config.get("GAME_PATH","")

    if not game_path or game_path == "" or not "BLEACH Rebirth of Souls" in game_path:
        flag = True
        while(flag):
            messagebox.showinfo("Bleach not found","BLEACH_Rebirth_of_Souls.exe not found. You can find it in your steam folder, press ok then select it")
            game_path = filedialog.askopenfilename(title="Select Bleach rebirth of souls",filetypes=[("Executable files", "*.exe")])
            
            if game_path == "":
                exit()
            
            if"BLEACH_Rebirth_of_Souls.exe" in game_path:
                flag = False

        parent_dir = os.path.dirname(game_path)
        game_path = str(parent_dir)
        config["GAME_PATH"] = game_path
        with open(config_path, "w") as f:
            json.dump(config, f)

   

    def injectFolder(files,folderName,fullFolder=True):
            folder_src = os.path.join(BASE_DIR,"GameVersions",f"{files}",f'{folderName}')
            folder_dst = os.path.join(game_path,f'{folderName}')
            
            if fullFolder:
                try:
                    subprocess.run(["robocopy",folder_src,folder_dst,"/MIR"],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
                except Exception as e:
                    shutil.rmtree(folder_dst)
                    shutil.copytree(folder_src, folder_dst)
            else:
                shutil.copytree(folder_src, folder_dst,dirs_exist_ok=True)
    
    def injectEffects(files,effectFolder):
        effect_src = os.path.join(BASE_DIR,"GameVersions",f"{files}",f'{effectFolder}',"Effect","spfx","com")
        effect_dst = os.path.join(game_path,f'{effectFolder}',"Effect","spfx","com")
        try:
            subprocess.run(["robocopy",effect_src,effect_dst,"/MIR"],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            shutil.rmtree(effect_dst)
            shutil.copytree(effect_src, effect_dst)

            

    def injectPerformanceFiles(folderName,lowspecmodornot):
        try:
            shutil.copytree(os.path.join(BASE_DIR,"Files","Spec Mod",f'{folderName}',f'{lowspecmodornot}'),
                            os.path.join(game_path,"00HIGH","Effect","spfx","com"),dirs_exist_ok=True)
            shutil.copytree(os.path.join(BASE_DIR,"Files","Spec Mod",f'{folderName}',f'{lowspecmodornot}'),
                            os.path.join(game_path,"01MIDDLE","Effect","spfx","com"),dirs_exist_ok=True)
        except Exception as e:
            print(f"Error injecting performance files: {e}")
    
    def repair():
        messagebox.showinfo("Repair", "Please select the BLEACH_Rebirth_of_Souls.exe file from a clean backup folder of the game (your backup folder, not your main Bros folder)")
        repair_game_path = ""
        parent_dir = ""
        if not repair_game_path or repair_game_path == "" or not "BLEACH Rebirth of Souls" in repair_game_path:
            flag = True
            while(flag):
                repair_game_path = filedialog.askopenfilename(title="Select Bleach rebirth of souls",filetypes=[("Executable files", "*.exe")])

                if repair_game_path == "":
                    messagebox.showinfo("Repair", "You cancelled the repair process.")
                    return
                elif"BLEACH_Rebirth_of_Souls.exe" in repair_game_path:
                    parent_dir = os.path.dirname(repair_game_path)
                    repair_game_path = str(parent_dir)
                    if repair_game_path == config["GAME_PATH"]:
                        messagebox.showerror("Error", "You selected the same folder as your main game folder. Please select a backup folder.")
                    else:
                        flag = False
                else : 
                    messagebox.showerror("Error", "You did not select the correct file. Please select the BLEACH_Rebirth_of_Souls.exe file of your backup folder")
        
       
        messagebox.showinfo("Repair", "Repairing files. Please wait")
        repairPage.tkraise()
        window.update()
        
        repairWaitOstPath = os.path.join(BASE_DIR,"ressources","RepairWaitOst.wav")
        repairEndOstPath = os.path.join(BASE_DIR,"ressources","RepairEndOst.wav")
        
        
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
            winsound.PlaySound(repairWaitOstPath, winsound.SND_ASYNC | winsound.SND_LOOP)
        except:
            pass
        
        try:
            subprocess.run([
                "robocopy", repair_game_path, game_path, "/E", "/XO"
            ], capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
        except:
            shutil.copytree(repair_game_path, game_path, dirs_exist_ok=True)
       
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
            winsound.PlaySound(repairEndOstPath, winsound.SND_ASYNC)
        except:
            pass
        messagebox.showinfo("Repair", "Files repaired successfully!")
        backToMainMenu()
        launcherOstPath = os.path.join(BASE_DIR,"ressources","LauncherOst.wav")
        
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
            winsound.PlaySound(launcherOstPath, winsound.SND_ASYNC | winsound.SND_LOOP)
        except:
            pass

    def setup_matchmaking(target_path, gameVersion):
        """Install the in-game matchmaking loader (dinput8.dll) and stamp a
        match code so only players on the SAME patch version + build match.
        Vanilla players have no loader and are excluded automatically."""
        import zlib
        src = os.path.join(BASE_DIR, "Files", "Matchmaking", "dinput8.dll")
        try:
            shutil.copy(src, os.path.join(target_path, "dinput8.dll"))
        except Exception as e:
            print(f"[matchmaking] could not install dinput8.dll: {e}")
            return
        # Match pool is derived AUTOMATICALLY from the current GitHub build
        # (the commit SHA from get_snapshot()) plus the selected game version.
        # crc32 turns the SHA (hex letters + digits) into a number. Every push
        # yields a new SHA -> a fresh pool, so players on a different build /
        # game version / vanilla won't match you. No manual bumping needed.
        build = get_snapshot() or "unknown"
        seed = f"{build}|{gameVersion}"
        code = 100000 + (zlib.crc32(seed.encode("utf-8")) % 800000)
        try:
            with open(os.path.join(target_path, "patch_ranked.txt"), "w") as f:
                f.write(str(code) + "\n")
        except Exception as e:
            print(f"[matchmaking] could not write match code: {e}")

    def remove_matchmaking(target_path):
        """Revert online segregation: remove the loader so vanilla launches
        cleanly under EasyAntiCheat."""
        p = os.path.join(target_path, "dinput8.dll")
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception as e:
            print(f"[matchmaking] could not remove dinput8.dll: {e}")

    def launch_patched(target_path):
        """Launch the patched game. On Windows, start the .exe directly (required
        so EasyAntiCheat doesn't block the injected dinput8.dll -- crash otherwise).
        On Linux/macOS a Windows .exe can't be exec'd directly ([Errno 8] Exec
        format error) -- it only runs through Steam/Proton -- so launch it via
        Steam's app URL instead. Steam must be running for online play."""
        exe = os.path.join(target_path, "BLEACH_Rebirth_of_Souls.exe")
        if platform.system() != "Windows":
            try:
                open_file("steam://rungameid/1689620")
            except Exception as e:
                print(f"Error launching patched game: {e}")
            return
        try:
            subprocess.Popen([exe], cwd=target_path)
        except OSError as e:
            if getattr(e, "winerror", None) == 740:
                # exe's manifest requires elevation — Popen/CreateProcess can't
                # trigger the UAC prompt itself, ShellExecuteW with "runas" can.
                try:
                    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, None, target_path, 1)
                except Exception as e2:
                    print(f"Error launching patched game (elevated): {e2}")
            else:
                print(f"Error launching patched game: {e}")
        except Exception as e:
            print(f"Error launching patched game: {e}")

    def launch(gameVersion):
        pulling_from_git()
        if not os.path.exists(os.path.join(BASE_DIR,"GameModes","TeamBattle","TokenOpen.txt")):
            config["TEAM_BATTLE"] = "OFF"
        try:
            #folder injection
            injectFolder(gameVersion,"Script")
            injectFolder(gameVersion,"Motion")
            injectFolder(gameVersion,"00HIGH",False)
            injectFolder(gameVersion,"01MIDDLE",False)



            #ost choice
            #ostFolder = ""
                #if config["OST_MOD"] == "ON":
                    #ostFolder = "Mod"
                #else : 
                    #ostFolder = "Default"
                #ostPath = os.path.join(BASE_DIR,"Files","OST",f"{ostFolder}","bgm.bnk")
                #if os.path.exists(ostPath):
                    #shutil.copy(
                        #ostPath,
                        #os.path.join(game_path, "Sound")
                    #)

        
            #Performance Mode injection
            shutil.copytree(os.path.join(BASE_DIR,"Files","Spec Mod",'reverse_globe',f'{config["reverse_globe"]}',"high"),
                        os.path.join(game_path,"00HIGH","Effect","spfx","com"),dirs_exist_ok=True)
        
            shutil.copytree(os.path.join(BASE_DIR,"Files","Spec Mod",'reverse_globe',f'{config["reverse_globe"]}',"middle"),
                        os.path.join(game_path,"01MIDDLE","Effect","spfx","com"),dirs_exist_ok=True)
            
            for folder in os.listdir(os.path.join(BASE_DIR,"Files","Spec Mod")):
                if folder != "reverse_globe":
                    injectPerformanceFiles(folder,config[folder])
        
            reworkPath = os.path.join(BASE_DIR,"Reworks")
            for rework in reworks:
                if rework != "OFF":
                    scriptPath = os.path.join(reworkPath,rework,"Script")
                    motionPath = os.path.join(reworkPath,rework,"Motion")
                
                    if os.path.exists(scriptPath):
                        shutil.copytree(scriptPath,os.path.join(game_path,"Script"),dirs_exist_ok=True)
                    if os.path.exists(motionPath):
                        shutil.copytree(motionPath,os.path.join(game_path,"Motion"),dirs_exist_ok=True)
                

            #gamemode injection
            if gameMode != "DEFAULT":
                srcPath = os.path.join(BASE_DIR,"GameModes",f"{gameMode}","Script")
                dstPath = os.path.join(game_path,"Script")
            
            
                shutil.copytree(srcPath, dstPath, dirs_exist_ok=True)
                srcPath = os.path.join(BASE_DIR,"GameModes",f"{gameMode}","Script")
                dstPath = os.path.join(game_path,"Script")
            
                shutil.copytree(srcPath, dstPath, dirs_exist_ok=True)

            
            #team battle injection
            if config["TEAM_BATTLE"] == "ON":
                srcPath = os.path.join(BASE_DIR,"GameModes","TeamBattle")
                dstPath = os.path.join(game_path,"Script")   
                shutil.copy(
                    os.path.join(srcPath,"CharaStatus.fsv"),
                    os.path.join(dstPath,"CharaStatus.fsv"))
            

            forlater = """
            else:
                src = Path(os.path.join(BASE_DIR,"Files",choice))
                dst = Path(game_path)

                dst.mkdir(parents=True,exist_ok=True)

                for item in src.rglob("*"):
                    if item.is_file:
                        relative_path = item.relative_to(src)
                        target_file = dst / relative_path

                        target_file.parent.mkdir(parents=True,exist_ok=True)
                        shutil.copy2(item,target_file)
                """

            # --- matchmaking segregation + EAC-aware launch --------------------
            # Only true Vanilla launches via Steam (EAC on, no loader). Every
            # other version - Community Patch AND any other custom version
            # (e.g. a future variant) - launches the exe directly (EAC off,
            # required for the loader). Each one still gets its OWN matchmaking
            # pool automatically: setup_matchmaking's seed includes gameVersion,
            # so a Community Patch player and an "other version" player will
            # never be given the same match code even though both skip Steam.
            VANILLA_VERSION = "Bleach Rebirth of Souls"
            if gameVersion != VANILLA_VERSION:
                setup_matchmaking(game_path, gameVersion)
                launch_patched(game_path)
            else:
                remove_matchmaking(game_path)
                try:
                    open_file("steam://rungameid/1689620")
                except:
                    print("Error launching game")
        except Exception as e:
            messagebox.showerror(
                "Launch Error",
                f"Something went wrong while preparing '{gameVersion}' for launch:\n\n{e}\n\n"
                "The game was not launched. Please check that this version's folder "
                "under GameVersions has all required subfolders (Script, Motion, 00High, 01MIDDLE)."
            )
            return

        window.destroy()
        
        

    def readBalanceChanges():
        webbrowser.open("https://rebalance-of-souls.github.io/reBalanceOfSouls.github.io/")
        latestChangesPath = os.path.join(BASE_DIR,"BalanceChanges","LatestChanges.txt")
       
        try:
            open_file(latestChangesPath)
        except:
            print("Error opening LatestChanges.txt")
    
    def readCredits():
        creditsFile = os.path.join(BASE_DIR,"Credits","credits.txt")
        if os.path.exists(creditsFile):
            try:
                open_file(creditsFile)
            except:
                print("Error opening credits.txt")


        saveJson()

    def changeGamePath():
        flag = True
        firstTime = True
        while(flag):
            game_path = filedialog.askopenfilename(title="Select Bleach rebirth of souls",filetypes=[("Executable files", "*.exe")])
            if"BLEACH_Rebirth_of_Souls.exe" in game_path:
                flag = False
            elif firstTime:
                firstTime = False
                messagebox.showerror("Error","BLEACH_Rebirth_of_Souls.exe not found")
                

        parent_dir = os.path.dirname(game_path)
        game_path = str(parent_dir)
        config["GAME_PATH"] = game_path

        with open(config_path, "w") as f:
            json.dump(config, f)
            
        labelGamePath.config(text=f'Current game path : {game_path}')
        
   
    def gameModesMenu():
        gameModesPage.tkraise()

    

    #box
    container = Frame(window, bg=bgcolor)
    container.pack(expand=YES, fill=BOTH, padx=60, pady=6)
    mainPage = Frame(container,bg=bgcolor)
    settingsPage = Frame(container,bg=bgcolor)
    gameModesPage = Frame(container,bg=bgcolor)
    repairPage = Frame(container,bg=bgcolor)
    reworksPage = Frame(container,bg=bgcolor)

    

    titleText = "Bleach Rebirth of Souls community patch launcher"
    subTitleText = "made by Nilsix :3"
    #labels
    labelTitle = Label(mainPage, text=titleText, font=("Arial",30),bg=bgcolor,fg=labelcolor)
    labelSubTitle = Label(mainPage,text=subTitleText,font=("Courrier",20),bg=bgcolor,fg=labelcolor)
    labelTitleSettings = Label(settingsPage, text=titleText, font=("Arial",30),bg=bgcolor,fg=labelcolor)
    labelSubTitleSettings = Label(settingsPage,text=subTitleText,font=("Courrier",20),bg=bgcolor,fg=labelcolor)
    labelTitleGameModes = Label(gameModesPage, text=titleText, font=("Arial",30),bg=bgcolor,fg=labelcolor)
    labelSubTitleGameModes = Label(gameModesPage,text=subTitleText,font=("Courrier",20),bg=bgcolor,fg=labelcolor)
    labelTitleRepair = Label(repairPage, text=titleText, font=("Arial",30),bg=bgcolor,fg=labelcolor)
    labelSubTitleRepair = Label(repairPage,text=subTitleText,font=("Courrier",20),bg=bgcolor,fg=labelcolor)
    labelRepairText = Label(repairPage,text="Repairing Files",font=("Courrier",15),bg=bgcolor,fg=labelcolor)
    labelTitleReworks = Label(reworksPage, text=titleText, font=("Arial",30),bg=bgcolor,fg=labelcolor)
    labelSubTitleReworks = Label(reworksPage,text=subTitleText,font=("Courrier",20),bg=bgcolor,fg=labelcolor)
    labelWarning = Label(mainPage, text="Warning : Please only use the non vanilla features in room matches online, not in casual or ranked matches",font=("Courrier",15),bg=bgcolor,fg=labelcolor)
    labelGamePath = Label(mainPage,text=f'Current game path : {game_path}',font=("Courrier",15),bg=bgcolor,fg=labelcolor)
    # Version + live online-code panel. Each underlined term shows a short
    # explanation on hover (reuses the Tooltip class) so the numbers aren't confusing.
    COMMUNITY_VERSION = "Bleach Rebirth of Souls Community Patch"
    LATEST_STRING = get_latest()
    _have_latest  = LATEST_STRING not in ("", "unknown")
    _up_to_date   = _have_latest and (VERSION_STRING == LATEST_STRING)
    MASTER_CODE   = compute_match_code(LATEST_STRING if _have_latest else VERSION_STRING, COMMUNITY_VERSION)
    _your_code    = read_loaded_code()

    versionPanel = Frame(mainPage, bg=bgcolor)
    def _term(parent, text, tip):
        lbl = Label(parent, text=text, font=("Courrier",12,"underline"),
                    bg=bgcolor, fg="#F3CDEC", cursor="question_arrow")
        Tooltip(lbl, tip)
        return lbl
    def _val(parent, text, fg=labelcolor):
        return Label(parent, text=text, font=("Courrier",12), bg=bgcolor, fg=fg)

    _status1 = "(up to date)" if _up_to_date else ("(update available - relaunch)" if _have_latest else "(offline)")
    _term(versionPanel, "Current version",
          "The patch build you have installed right now (short git commit hash).").grid(row=0,column=0,sticky="e",pady=1)
    _val(versionPanel, f" : {VERSION_STRING}").grid(row=0,column=1,sticky="w",padx=(0,22))
    _term(versionPanel, "Latest version",
          "The newest patch build published on GitHub. If it differs from Current, an update is available - relaunch to get it.").grid(row=0,column=2,sticky="e",pady=1)
    _val(versionPanel, f" : {LATEST_STRING}  {_status1}",
         fg=(labelcolor if (_up_to_date or not _have_latest) else "#FFD27F")).grid(row=0,column=3,sticky="w")

    _term(versionPanel, "Master online code",
          "The room code every player on the LATEST build uses online. You only match players whose code equals this one.").grid(row=1,column=0,sticky="e",pady=1)
    _val(versionPanel, f" : {MASTER_CODE}").grid(row=1,column=1,sticky="w",padx=(0,22))
    _term(versionPanel, "Your loaded code",
          "The room code that actually installed on your machine the last time the game ran (read from patch_ranked.log). It should equal Master online code.").grid(row=1,column=2,sticky="e",pady=1)
    if _your_code:
        _ok = str(_your_code) == str(MASTER_CODE)
        _val(versionPanel, f" : {_your_code}  " + ("(OK)" if _ok else "(mismatch)"),
             fg=("#9CE59C" if _ok else "#FF9B9B")).grid(row=1,column=3,sticky="w")
    else:
        _val(versionPanel, " : (not set yet)", fg="#FFD27F").grid(row=1,column=3,sticky="w")

    Label(versionPanel,
          text="Launch the game once through the launcher to update your online code. "
               "If it still doesn't match, update your launcher / reinstall the patch.",
          font=("Courrier",9), bg=bgcolor, fg="#C9A9C2", wraplength=1000, justify="center"
          ).grid(row=2,column=0,columnspan=4,pady=(5,0))
    
    brosVersion = StringVar()
    gameVersionsList = []
    gameVersionsPath = os.path.join(BASE_DIR,"GameVersions")
    for folder in os.listdir(gameVersionsPath):
        gameVersionsList.append(folder)
    brosVersionList = ttk.Combobox(
        mainPage,
        textvariable=brosVersion,
        values=gameVersionsList,
        state="readonly",
        font=("Courrier",25)
    )

    brosVersionList.set("Choose a game version")

    def preLauncher():
        if brosVersionList.get() != "Choose a game version":
            launch(brosVersionList.get())
        
    def performanceSettingsMenu():
        settingsPage.tkraise()

    def adjustAwakeningAuraSettings():
        if config["awakeningaura"] == "original":
            config["awakeningaura"] = "lowspec"
        else:
            config["awakeningaura"] = "original"
        awakeningAuraButton.config(text=f'remove awakening aura : currently {"OFF" if config["awakeningaura"] == "original" else "ON"}')
        
    
    def adjustBreakerGrabSettings():
        if config["breaker_grab"] == "original":
            config["breaker_grab"] = "lowspec"
        else:
            config["breaker_grab"] = "original"

        breakerGrabButton.config(
            text=f'remove breaker grab effect : currently {"OFF" if config["breaker_grab"] == "original" else "ON"}'
        )
        

    def adjustHakugekiSettings():
        if config["hakugeki"] == "original":
            config["hakugeki"] = "lowspec"
        else:
            config["hakugeki"] = "original"
        hakugekiButton.config(text=f'remove hakugeki effect : currently {"OFF" if config["hakugeki"] == "original" else "ON"}')
        
    
    def adjustHitEffectSettings():
        if config["hit"] == "original":
            config["hit"] = "lowspec"
        else:
            config["hit"] = "original"
        hitEffectButton.config(text=f'remove hit effect : currently {"OFF" if config["hit"] == "original" else "ON"}')  
        
    
    def adjustReverseGlobeSettings():
        if config["reverse_globe"] == "original":
            config["reverse_globe"] = "lowspec"
        else:
            config["reverse_globe"] = "original"
        reverseGlobeButton.config(text=f'remove reverse globe effect : currently {"OFF" if config["reverse_globe"] == "original" else "ON"}')  
        
    
    def adjustSkillActivationSettings():
        if config["skill_activation"] == "original":
            config["skill_activation"] = "lowspec"
        else:
            config["skill_activation"] = "original"
        skillActivationButton.config(text=f'remove skill activation effect : currently {"OFF" if config["skill_activation"] == "original" else "ON"}')  
        

    def backToMainMenu():
        saveJson()
        mainPage.tkraise()

    def baseOnlyFunc():
        global gameMode
        if gameMode == "BaseOnly":
            gameMode = "DEFAULT"
        else:
            gameMode = "BaseOnly"
        actualiseGameModeButtons()
    
    def teamBattleFunc():
        if not os.path.exists(os.path.join(BASE_DIR,"GameModes","TeamBattle","TokenOpen.txt")):
            config["TEAM_BATTLE"] = "OFF"
            saveJson()
            messagebox.showinfo("Team Battle", "You need to contact a Team Battle host to be able to join a team battle, for that, ping one on the discord using @Team Battle Host")
            return
        config["TEAM_BATTLE"] = "ON" if config["TEAM_BATTLE"] == "OFF" else "OFF"
        saveJson()
        teamBattleButton.config(text=f'Team Battle : (Currently {"ON" if config["TEAM_BATTLE"] == "ON" else "OFF"})')
    
    def instantEvoAndSublimationFunc():
        global gameMode
        if gameMode == "InstantEvoAndSublimation":
            gameMode = "DEFAULT"
        else:
            gameMode = "InstantEvoAndSublimation"
        actualiseGameModeButtons()
    
    def eightKonpakusFunc():
        global gameMode
        if gameMode == "EightKonpakus":
            gameMode = "DEFAULT"
        else:
            gameMode = "EightKonpakus"
        actualiseGameModeButtons()

    def extraKonpakuFunc():
        global gameMode
        if gameMode == "ExtraKonpaku":
            gameMode = "DEFAULT"
        else:
            gameMode = "ExtraKonpaku"
        actualiseGameModeButtons()

    def suddenDeathFunc():
        global gameMode
        if gameMode == "SuddenDeath":
            gameMode = "DEFAULT"
        else:
            gameMode = "SuddenDeath"
        actualiseGameModeButtons()

    def actualiseGameModeButtons():
        baseOnlyButton.config(text=f'Base Only : (Currently {"ON" if gameMode == "BaseOnly" else "OFF"})')
        instantEvoAndSublimation.config(text=f'Instant Evo and Sublimation : (Currently {"ON" if gameMode == "InstantEvoAndSublimation" else "OFF"})')
        eightKonpakus.config(text=f'8 Konpakus : (Currently {"ON" if gameMode == "EightKonpakus" else "OFF"})')
        extraKonpaku.config(text=f'Extra Konpaku : (Currently {"ON" if gameMode == "ExtraKonpaku" else "OFF"})')
        suddenDeath.config(text=f'Sudden Death : (Currently {"ON" if gameMode == "SuddenDeath" else "OFF"})')
    
    def unlockDangaiIchigo():
        result = messagebox.askyesno("Unlock Dangai Ichigo", "Unlocking Dangai Ichigo this way will reset your settings and ranked progress , are you sure you want to continue?")
        theDangaiFiles = os.path.join(BASE_DIR,"ressources","savedata.bin")
        if result:
            appdataPath = os.getenv("APPDATA")
            try:
                saveDataPath = os.path.join(appdataPath,"BLEACH Rebirth of Souls","Savedata")
                for folder in os.listdir(saveDataPath):
                    shutil.copy(theDangaiFiles, os.path.join(saveDataPath, folder))
            except Exception as e:
                messagebox.showerror("Error", f"Error: {e}")
                return
            # Copy the dangai files to the save data path
            #shutil.copy2(theDangaiFiles, saveDataPath)
            messagebox.showinfo("Dangai Ichigo unlocked", "Dangai Ichigo unlocked successfully!")
    
    def refreshLauncher():
        result = pulling_from_git()
        if result.returncode == 0:
            messagebox.showinfo("Refresh", "Launcher refreshed successfully!")
        else:
            messagebox.showerror("Refresh", f"Error refreshing launcher: {result.stderr}")
    
    def reworksMenu():
        reworksPage.tkraise()
   
    def byakuyaReworkToggle():
        global reworks
        if reworks[0] == "OFF":
            reworks[0] = "Byakuya"
        else:
            reworks[0] = "OFF"
        reworksByakuyaButton.config(text=f'Byakuya Rework : {"ON" if reworks[0] == "Byakuya" else "OFF"}')

    textSize = 12
    paddingYvalue = 5
    #buttons
    launchButton = Button(mainPage,text="Launch the game",font=("Courrier",textSize),bg="white",fg=bgcolor,command=preLauncher)
    joinDiscordButton = Button(mainPage,text="Join our discord :) ",font=("Courrier",textSize),command=lambda : webbrowser.open("https://discord.gg/fSbsZE3qSZ"))
    changeGamePathButton =  Button(mainPage,text=f'Change your game path',font=("Courrier",textSize),bg="white",fg=bgcolor,command=changeGamePath)
    readBalanceChangesButton =  Button(mainPage,text=f'Read balance changes',font=("Courrier",textSize),bg="white",fg=bgcolor,command=readBalanceChanges)
    lowSpecButton =  Button(mainPage,text=f'FPS Booster settings',font=("Courrier",textSize),bg="white",fg=bgcolor,command=performanceSettingsMenu)
    CreditsButton = Button(mainPage,text="Credits",font=("Courrier",textSize),bg="white",fg=bgcolor,command=readCredits)
    gameModesButton = Button(mainPage,text="Game Modes",font=("Courrier",textSize),bg="white",fg=bgcolor,command=gameModesMenu)
    unlockDangaiIchigoButton = Button(mainPage,text="Unlock Dangai Ichigo",font=("Courrier",textSize),bg="white",fg=bgcolor,command=unlockDangaiIchigo)
    repairButton = Button(mainPage,text="Repair files",font=("Courrier",textSize),bg="white",fg=bgcolor,command=repair)
    refreshLauncherButton = Button(mainPage,text="Refresh launcher",font=("Courrier",textSize),bg="white",fg=bgcolor,command=refreshLauncher)
    reworksPageButton = Button(mainPage,text="Reworks",font=("Courrier",textSize),bg="white",fg=bgcolor,command=reworksMenu)
   


    # Apply hover effects to main-page buttons 
    add_hover(launchButton,          "Launch the game using the version selected in the dropdown above.")
    add_hover(joinDiscordButton,     "Open the community Discord server in your browser.")
    add_hover(changeGamePathButton,  "Change the folder path where your copy of Bleach Rebirth of Souls is installed.")
    add_hover(readBalanceChangesButton, "Open the latest balance-changes notes")
    add_hover(gameModesButton,       "Switch between different game modes (Base only, 8 konpaku, etc...)")
    add_hover(lowSpecButton,         "Toggle per-effect FPS booster settings to improve performance on lower-end PCs.")
    add_hover(repairButton,          "Restore your game files from a clean backup copy of the game.")
    add_hover(CreditsButton,         "View the credits for the mods used in this patch.")
    add_hover(unlockDangaiIchigoButton, "Unlocks Dangai Ichigo")
    add_hover(refreshLauncherButton, "Refresh the launcher to get the latest updates.")

    #pack
    labelTitle.pack()
    labelSubTitle.pack()
    versionPanel.pack(pady=(2,4))
    #labelWarning.pack(fill=X)
    labelGamePath.pack(fill=X)
    brosVersionList.pack(pady=paddingYvalue,fill=X)
    launchButton.pack()
    joinDiscordButton.pack(pady=paddingYvalue,fill=X)
    changeGamePathButton.pack(pady=paddingYvalue,fill=X)
    readBalanceChangesButton.pack(pady=paddingYvalue,fill=X)
    gameModesButton.pack(pady=paddingYvalue,fill=X)
    #ostSettingsButton.pack(pady=paddingYvalue,fill=X)
    lowSpecButton.pack(pady=paddingYvalue,fill=X)
    repairButton.pack(pady=paddingYvalue,fill=X)
    unlockDangaiIchigoButton.pack(pady=paddingYvalue,fill=X)
    refreshLauncherButton.pack(pady=paddingYvalue,fill=X)
    #reworksPageButton.pack(pady=paddingYvalue,fill=X)
    CreditsButton.pack(pady=paddingYvalue,fill=X)


    labelTitleSettings.pack()
    labelSubTitleSettings.pack()

    labelTitleReworks.pack()
    labelSubTitleReworks.pack()


    #Settings page
    awakeningAuraButton = Button(
    settingsPage,
    text=f'remove awakening aura : currently {"OFF" if config["awakeningaura"] == "original" else "ON"}',
    font=("Courrier", textSize),
    bg="white",
    fg=bgcolor,
    command=adjustAwakeningAuraSettings
)
    awakeningAuraButton.pack(pady=paddingYvalue, fill=X)


    breakerGrabButton = Button(
        settingsPage,
        text=f'remove breaker grab effect : currently {"OFF" if config["breaker_grab"] == "original" else "ON"}',
        font=("Courrier", textSize),
        bg="white",
        fg=bgcolor,
        command=adjustBreakerGrabSettings
    )
    breakerGrabButton.pack(pady=paddingYvalue, fill=X)


    hakugekiButton = Button(
        settingsPage,
        text=f'remove hakugeki effect : currently {"OFF" if config["hakugeki"] == "original" else "ON"}',
        font=("Courrier", textSize),
        bg="white",
        fg=bgcolor,
        command=adjustHakugekiSettings
    )
    hakugekiButton.pack(pady=paddingYvalue, fill=X)


    hitEffectButton = Button(
        settingsPage,
        text=f'remove hit effect : currently {"OFF" if config["hit"] == "original" else "ON"}',
        font=("Courrier", textSize),
        bg="white",
        fg=bgcolor,
        command=adjustHitEffectSettings
    )
    hitEffectButton.pack(pady=paddingYvalue, fill=X)


    reverseGlobeButton = Button(
        settingsPage,
        text=f'remove reverse globe effect : currently {"OFF" if config["reverse_globe"] == "original" else "ON"}',
        font=("Courrier", textSize),
        bg="white",
        fg=bgcolor,
        command=adjustReverseGlobeSettings
    )
    reverseGlobeButton.pack(pady=paddingYvalue, fill=X)


    skillActivationButton = Button(
        settingsPage,
        text=f'remove skill activation effect : currently {"OFF" if config["skill_activation"] == "original" else "ON"}',
        font=("Courrier", textSize),
        bg="white",
        fg=bgcolor,
        command=adjustSkillActivationSettings 
    )
    skillActivationButton.pack(pady=paddingYvalue, fill=X)
    
    mainMenuButton = Button(
        settingsPage,
        text="Main Menu",
        font=("Courrier", textSize),
        bg="white",
        fg=bgcolor,
        command=backToMainMenu
    )

    mainMenuButton.pack(pady=paddingYvalue,fill=X)

    # Apply hover effects to settings-page buttons
    add_hover(awakeningAuraButton,    "Toggle the awakening aura visual effect on/off to save GPU performance.")
    add_hover(breakerGrabButton,      "Toggle the breaker grab screen effect on/off.")
    add_hover(hakugekiButton,         "Toggle the Hakugeki flash effect on/off.")
    add_hover(hitEffectButton,        "Toggle hit impact visual effects on/off.")
    add_hover(reverseGlobeButton,     "Toggle the reverse globe screen effect on/off.")
    add_hover(skillActivationButton,  "Toggle the skill activation flash effect on/off.")
    add_hover(mainMenuButton,         "Return to the main menu.")

    #game modes page
    labelTitleGameModes.pack(pady=paddingYvalue)
    labelSubTitleGameModes.pack(pady=paddingYvalue)

    gameModesMenuButton = Button(
        gameModesPage,
        text="Main Menu",
        font=("Courrier", textSize),
        bg="white",
        fg=bgcolor,
        command=backToMainMenu
    )

    baseOnlyButton = Button(
        gameModesPage,
        text=f'Base Only : (Currently {"ON" if gameMode == "BaseOnly" else "OFF"})',
        font=("Courrier", textSize),
        bg="white",
        fg=bgcolor,
        command=baseOnlyFunc
    )

    teamBattleButton = Button(
        gameModesPage,
        text=f'Team Battle : (Currently {"ON" if config["TEAM_BATTLE"] == "ON" else "OFF"})',
        font=("Courrier", textSize),
        bg="white",
        fg=bgcolor,
        command=teamBattleFunc
    )
    instantEvoAndSublimation = Button(
        gameModesPage,
        text=f'Instant Evo and Sublimation : (Currently {"ON" if gameMode == "InstantEvoAndSublimation" else "OFF"})',
        font=("Courrier", textSize),
        bg="white",
        fg=bgcolor,
        command=instantEvoAndSublimationFunc
    )

    eightKonpakus = Button(
        gameModesPage,
        text=f'8 Konpakus : (Currently {"ON" if gameMode == "EightKonpakus" else "OFF"})',
        font=("Courrier", textSize),
        bg="white",
        fg=bgcolor,
        command=eightKonpakusFunc
    )

    extraKonpaku = Button(
        gameModesPage,
        text=f'Extra Konpaku : (Currently {"ON" if gameMode == "ExtraKonpaku" else "OFF"})',
        font=("Courrier", textSize),
        bg="white",
        fg=bgcolor,
        command=extraKonpakuFunc
    )

    suddenDeath = Button(
        gameModesPage,
        text=f'Sudden Death : (Currently {"ON" if gameMode == "SuddenDeath" else "OFF"})',
        font=("Courrier", textSize),
        bg="white",
        fg=bgcolor,
        command=suddenDeathFunc
    )
    teamBattleButton.pack(pady=paddingYvalue, fill=X)
    instantEvoAndSublimation.pack(pady=paddingYvalue, fill=X)
    baseOnlyButton.pack(pady=paddingYvalue, fill=X)
    eightKonpakus.pack(pady=paddingYvalue, fill=X)
    extraKonpaku.pack(pady=paddingYvalue, fill=X)
    suddenDeath.pack(pady=paddingYvalue, fill=X)
    gameModesMenuButton.pack(pady=paddingYvalue, fill=X)

    # Apply hover effects to game-modes-page buttons
    add_hover(teamBattleButton,        "Toggle Team Battle mode: allows team fights.")
    add_hover(instantEvoAndSublimation,"Toggle Instant Evolution & Sublimation: evolution and sublimation happen immediately.")
    add_hover(baseOnlyButton,          "Toggle Base Only mode: disables evolutions and sublimations entirely. Every character starts with 6 konpaku stocks")
    add_hover(eightKonpakus,           "Toggle 8 Konpakus mode: each player starts with 8 Konpaku stocks (revive characters start with 7).")
    add_hover(extraKonpaku,            "Toggle Extra Konpaku mode: gives every player extra Konpaku stocks.")
    add_hover(suddenDeath,             "Toggle Sudden Death mode.")
    add_hover(gameModesMenuButton,     "Return to the main menu.")

    #repairPage
    labelRepairText = Label(
        repairPage,
        text="Repairing files. Please wait",
        font=("Courrier", 35),
        bg=bgcolor,
        fg=labelcolor
    )

    labelSubtitleRepairText = Label(
        repairPage,
        text="Repairing files. Please wait",
        font=("Courrier", 20),
        bg=bgcolor,
        fg=labelcolor
    )
    

    labelTitleRepair.pack(pady=paddingYvalue)
    labelSubTitleRepair.pack(pady=paddingYvalue)
    labelRepairText.pack(pady=200)

    reworksByakuyaButton = Button(reworksPage,text=f'Byakuya Rework : {"ON" if reworks[0] == "Byakuya" else "OFF"}',font=("Courrier",textSize),bg="white",fg=bgcolor,command=byakuyaReworkToggle)
    reworksBackToMenuButton = Button(reworksPage,text="Back to menu",font=("Courrier",textSize),bg="white",fg=bgcolor,command=mainPage.tkraise)
    reworksByakuyaButton.pack(pady=paddingYvalue, fill=X)
    reworksBackToMenuButton.pack(pady=paddingYvalue, fill=X)

    # Let the stacked pages fill the whole container (so buttons stretch to width).
    container.grid_rowconfigure(0, weight=1)
    container.grid_columnconfigure(0, weight=1)
    for page in(mainPage,settingsPage,gameModesPage,repairPage,reworksPage):
        page.grid(row=0,column=0,sticky="nsew")
    mainPage.tkraise()

    def fit_window():
        # Size the window to exactly fit its content (the tallest stacked page,
        # since they all share row0/col0), capped to the screen, then centre it.
        # Crisp at native DPI + never clipped, whatever the monitor/scaling.
        window.update_idletasks()
        sw = window.winfo_screenwidth(); sh = window.winfo_screenheight()
        w = min(max(window.winfo_reqwidth(), 700), sw - 40)
        h = min(window.winfo_reqheight(), sh - 80)
        x = max(0, (sw - w) // 2); y = max(0, (sh - h) // 2 - 20)
        window.geometry(f"{w}x{h}+{x}+{y}")
    fit_window()
    window.deiconify()
    window.mainloop()
except Exception as e:
    try :
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 1)
    except:
        pass
    print(f'Error : {e}')
    input("Please ping the error to Nilsix")