import csv
import os     
import subprocess
import shutil
import json
import requests
import hashlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEAM_BATTLE_DIR = os.path.join(BASE_DIR,"..","GameModes","TeamBattle")
charastatusPath = os.path.join(BASE_DIR,"..","GameVersions","Bleach Rebirth of Souls Community Patch","Script","CharaStatus.fsv")


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

try:
    if os.path.exists(os.path.join(BASE_DIR,"..","adminConfig.json")):
        admin_config_path = os.path.join(BASE_DIR,"..","adminConfig.json")
        print("it does exist")
except:
        admin_config_path = None

admin_config = None
    
if admin_config_path is not None:
    with open(admin_config_path, "r") as f:
        admin_config = json.load(f)

def checkTokenOpen():
    if os.path.exists(os.path.join(TEAM_BATTLE_DIR,"TokenOpen.txt")):
        return True
    return False


def applyKonpakuChanges(id,value):
    revValue = value
    if id == "35" and value == 9:
        value = 5
    elif id == "01" or id == "20" or id =="5":
        if value == 9:
            value = 8
        revValue +=2

    id = "pl0"+id
    csvPath = os.path.join(TEAM_BATTLE_DIR,"CharaStatus.csv")
    with open(csvPath,"r",encoding="utf8") as f:
        rows = list(csv.DictReader(f))
        for row in rows:
            if row["_csv0"] == id:
                row["soul_num"] = value
                row["evo_soul_num"] = value
                row["rev_soul_num"] = revValue

    with open(csvPath,"w",newline="",encoding="utf-8") as f:
        writer = csv.DictWriter(f,fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

options = -1
if checkTokenOpen() == False:
    options = int(input("""Quit (0)
Open server (1)

Choose an option : """))

    if options == 1:
        
        open(os.path.join(TEAM_BATTLE_DIR,"TokenOpen.txt"), "w").close()
        shutil.copy(charastatusPath,os.path.join(TEAM_BATTLE_DIR,"CharaStatus.fsv"))
        shutil.copy(charastatusPath,os.path.join(TEAM_BATTLE_DIR,"originalCharaStatus","CharaStatus.fsv"))
        subprocess.run("convertToCsv.bat",shell=True,cwd=TEAM_BATTLE_DIR)
    exit()

options = int(input("""
Quit (0)               
Update CharaStatus (1)
Reset CharaStatus (2)
Close server (3)

Choose an option : """))
    
if options == 0:
    exit()
elif options == 1:
    print("""00 = ICHIGO KUROSAKI
01 = ICHIGO KUROSAKI (BANKAI)
02 = ICHIGO KUROSAKI (FINAL GETSUGATENSHO)
03 = URYU ISHIDA
04 = YASUTORA SADO
06 = KISUKE URAHARA
07 = YORUICHI SHIHOIN
08 = RENJI ABARAI
10 = RUKIA KUCHIKI
11 = SHUHEI HISAGI
12 = RANGIKU MATSUMOTO
13 = IZURU KIRA
14 = IKKAKU MADARAME
15 = YUMICHIKA AYASEGAWA
16 = SHIGEKUNI GENRYUSAI YAMAMOTO
17 = SOI FON
18 = GIN ICHIMARU
19 = RETSU UNOHANA
20 = SOSUKE AIZEN
22 = BYAKUYA KUCHIKI
23 = SAJIN KOMAMURA
24 = SHUNSUI KYORAKU
25 = KANAME TOSEN
26 = TOSHIRO HITSUGAYA
27 = KENPACHI ZARAKI
29 = MAYURI KUROTSUCHI 
31 = KAIEN SHIBA
32 = SHINJI HIRAKO
33 = COYOTE STARK
35 = TIER HALIBEL
36 = ULQUIORRA SHIFAR
37 = NNOITORA GILGA
38 = GRIMMJOW JEAGERJAQUES
39 = SZAYELAPORRO GRANTZ
42 = NELLIEL TU ODELSCHWANCK
50 = ICHIBE HOUSUBE 
51 = ICHIGO KUROSAKI TYBW
52 = YHWACH""")

    WinnerInput = input("\nWinner ID : ")
    winnerKonpakuRemaining = int(input("remaining konpakus : "))
    LoserInput = input("\nLoser ID : ")

    applyKonpakuChanges(WinnerInput, winnerKonpakuRemaining)
    applyKonpakuChanges(LoserInput, 9)
    subprocess.run([os.path.join(TEAM_BATTLE_DIR,"convertToFsvAndPush.bat")], shell=True)
    with open(admin_config_path,"w") as f:
        json.dump(admin_config,f)

        hash = hashlib.sha256(admin_config["HASH_VALUE"].encode()).hexdigest()
                
        if admin_config["ADMIN_ID"] == hash:
            webhook_url = "https://discord.com/api/webhooks/1529735486699212840/9rCA5O83KOJP8MTNiOykXuqoIJGg-fCdA6uyrFdZ2UD6SIzONsdi9Z_nGfYpzmRC9fX3"
            webhook_url2 = "https://discord.com/api/webhooks/1522537997751549972/AUYztUb1AS77vhsc6ERfeRYE9kNu0KLfem8HP9CGQDVe0lrkOeNarf8VlPGbrAyj-jeZ"
            try : 
                requests.post(webhook_url, json={"content": "Changes applied, you can now restart your game"})
                requests.post(webhook_url2, json={"content": "Launcher latest version : " + f"{get_snapshot()}"})

            except:
                pass
elif options == 2:
    subprocess.run([os.path.join(TEAM_BATTLE_DIR,"resetCharaStatus.bat")], shell=True)
elif options == 3:
    os.remove(os.path.join(TEAM_BATTLE_DIR,"TokenOpen.txt"))
    os.remove(os.path.join(TEAM_BATTLE_DIR,"CharaStatus.csv"))
    os.remove(os.path.join(TEAM_BATTLE_DIR,"CharaStatus.fsv"))
    os.remove(os.path.join(TEAM_BATTLE_DIR,"originalCharaStatus","CharaStatus.fsv"))
    os.remove(os.path.join(TEAM_BATTLE_DIR,"originalCharaStatus","CharaStatus.csv"))