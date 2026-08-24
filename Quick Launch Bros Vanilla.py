import os
import json
import shutil
import subprocess
import platform
import zlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

GAME_VERSION = "Bleach Rebirth of Souls" 

config_path = os.path.join(BASE_DIR, "Json", "config.json")
with open(config_path, "r") as f:
    config = json.load(f)

game_path = config.get("GAME_PATH", "")
if game_path == "":
    input("Your game path is empty, please run the normal launcher first to set a game path,press Enter to quit")
    exit()
gameMode = "DEFAULT"
reworks = ["OFF"]


def get_snapshot():
    try:
        result = subprocess.run(
            ["git", "-C", BASE_DIR, "rev-parse", "--short", "HEAD"],
            check=True, capture_output=True, text=True
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def pulling_from_git():
    # Ensure git can write the deep Effect/spfx/... paths that blow past the
    # legacy 260-char Windows limit. core.longpaths makes git use \\?\ extended
    # paths internally -- no admin, no registry change, no reboot. A partial
    # "Filename too long" clone then self-heals on launch: the objects are
    # already downloaded, so the reset --hard below writes the missing
    # long-path files with zero action from the user.
    subprocess.run(["git", "-C", BASE_DIR, "config", "core.longpaths", "true"], capture_output=True, text=True)
    if not os.path.exists(os.path.join(BASE_DIR, "BalanceLeadTools", "DevToken.txt")):
        subprocess.run(["git", "-C", BASE_DIR, "fetch"], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", BASE_DIR, "reset", "--hard", "origin/main"], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", BASE_DIR, "clean", "-fd", "-e", "Json"], check=True, capture_output=True, text=True)
    return subprocess.run(["git", "-C", BASE_DIR, "pull"], check=True, capture_output=True, text=True)


def open_file(path):
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.run(["open", path])
    else:
        subprocess.run(["xdg-open", path])


def injectFolder(files, folderName, fullFolder=True):
    folder_src = os.path.join(BASE_DIR, "GameVersions", f"{files}", f"{folderName}")
    folder_dst = os.path.join(game_path, f"{folderName}")
    if fullFolder:
        try:
            subprocess.run(["robocopy", folder_src, folder_dst, "/MIR"], capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            shutil.rmtree(folder_dst)
            shutil.copytree(folder_src, folder_dst)
    else:
        shutil.copytree(folder_src, folder_dst, dirs_exist_ok=True)


def injectPerformanceFiles(folderName, lowspecmodornot):
    try:
        shutil.copytree(os.path.join(BASE_DIR, "Files", "Spec Mod", f"{folderName}", f"{lowspecmodornot}"),
                         os.path.join(game_path, "00HIGH", "Effect", "spfx", "com"), dirs_exist_ok=True)
        shutil.copytree(os.path.join(BASE_DIR, "Files", "Spec Mod", f"{folderName}", f"{lowspecmodornot}"),
                         os.path.join(game_path, "01MIDDLE", "Effect", "spfx", "com"), dirs_exist_ok=True)
    except Exception as e:
        print(f"Error injecting performance files: {e}")


def setup_matchmaking(target_path, gameVersion):
    src = os.path.join(BASE_DIR, "Files", "Matchmaking", "dinput8.dll")
    try:
        shutil.copy(src, os.path.join(target_path, "dinput8.dll"))
    except Exception as e:
        print(f"[matchmaking] could not install dinput8.dll: {e}")
        return
    build = get_snapshot() or "unknown"
    seed = f"{build}|{gameVersion}"
    code = 100000 + (zlib.crc32(seed.encode("utf-8")) % 800000)
    try:
        with open(os.path.join(target_path, "patch_ranked.txt"), "w") as f:
            f.write(str(code) + "\n")
    except Exception as e:
        print(f"[matchmaking] could not write match code: {e}")


def remove_matchmaking(target_path):
    p = os.path.join(target_path, "dinput8.dll")
    try:
        if os.path.exists(p):
            os.remove(p)
    except Exception as e:
        print(f"[matchmaking] could not remove dinput8.dll: {e}")


def launch_patched(target_path):
    # On Windows start the .exe directly (needed so EasyAntiCheat doesn't block
    # the injected dinput8.dll). On Linux/macOS a Windows .exe can't be exec'd
    # directly (OSError: [Errno 8] Exec format error) -- it only runs through
    # Steam/Proton -- so launch it via Steam's app URL instead.
    exe = os.path.join(target_path, "BLEACH_Rebirth_of_Souls.exe")
    try:
        if platform.system() == "Windows":
            subprocess.Popen([exe], cwd=target_path)
        else:
            open_file("steam://rungameid/1689620")
    except Exception as e:
        print(f"Error launching patched game: {e}")


def launch(gameVersion):
    pulling_from_git()
    if not os.path.exists(os.path.join(BASE_DIR,"GameModes","TeamBattle","TokenOpen.txt")):
        config["TEAM_BATTLE"] = "OFF"
    try:
        injectFolder(gameVersion, "Script")
        injectFolder(gameVersion, "Motion")
        injectFolder(gameVersion, "00HIGH", False)
        injectFolder(gameVersion, "01MIDDLE", False)
        # Vanilla ships the STOCK Demo/ so that picking it undoes the shortened
        # intros and stage cameras the patch installs. Merge, never /MIR.
        if os.path.isdir(os.path.join(BASE_DIR, "GameVersions", gameVersion, "Demo")):
            injectFolder(gameVersion, "Demo", False)

        shutil.copytree(os.path.join(BASE_DIR, "Files", "Spec Mod", "reverse_globe", f'{config["reverse_globe"]}', "high"),
                         os.path.join(game_path, "00HIGH", "Effect", "spfx", "com"), dirs_exist_ok=True)
        shutil.copytree(os.path.join(BASE_DIR, "Files", "Spec Mod", "reverse_globe", f'{config["reverse_globe"]}', "middle"),
                         os.path.join(game_path, "01MIDDLE", "Effect", "spfx", "com"), dirs_exist_ok=True)

        for folder in os.listdir(os.path.join(BASE_DIR, "Files", "Spec Mod")):
            if folder != "reverse_globe":
                injectPerformanceFiles(folder, config[folder])

        reworkPath = os.path.join(BASE_DIR, "Reworks")
        for rework in reworks:
            if rework != "OFF":
                scriptPath = os.path.join(reworkPath, rework, "Script")
                motionPath = os.path.join(reworkPath, rework, "Motion")
                if os.path.exists(scriptPath):
                    shutil.copytree(scriptPath, os.path.join(game_path, "Script"), dirs_exist_ok=True)
                if os.path.exists(motionPath):
                    shutil.copytree(motionPath, os.path.join(game_path, "Motion"), dirs_exist_ok=True)

        if gameMode != "DEFAULT":
            srcPath = os.path.join(BASE_DIR, "GameModes", f"{gameMode}", "Script")
            dstPath = os.path.join(game_path, "Script")
            shutil.copytree(srcPath, dstPath, dirs_exist_ok=True)

        if config["TEAM_BATTLE"] == "ON":
            print("here")
            srcPath = os.path.join(BASE_DIR, "GameModes", "TeamBattle")
            dstPath = os.path.join(game_path, "Script")
            shutil.copy(os.path.join(srcPath, "CharaStatus.fsv"), os.path.join(dstPath, "CharaStatus.fsv"))

      
        remove_matchmaking(game_path)
        try:
            open_file("steam://rungameid/1689620")
        except Exception:
            print("Error launching game")

    except Exception as e:
        print(f"Launch Error while preparing '{gameVersion}' for launch:\n{e}")
        return


if __name__ == "__main__":
    launch(GAME_VERSION)