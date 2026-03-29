import os
import sys
import json
import shutil
import platform
import zipfile
import tempfile
import urllib.request
import subprocess
from datetime import datetime

# ==========================================
# MINECRANIX ONE-CLICK INSTALLER SCRIPT
# ==========================================

MODPACK_NAME = "Minecranix"
GITHUB_ZIP_URL = "https://github.com/crancorn-git/minecranix-modpack/archive/refs/heads/main.zip"

# The NeoForge version you are using (e.g. "21.1.65" for MC 1.21.1)
NEOFORGE_VERSION = "21.1.220"

# ==========================================
# ADVANCED SETTINGS (Usually don't need changing)
NEOFORGE_INSTALLER_URL = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{NEOFORGE_VERSION}/neoforge-{NEOFORGE_VERSION}-installer.jar"
LOADER_VERSION_ID = f"neoforge-{NEOFORGE_VERSION}"
# ==========================================

def get_minecraft_dir():
    """Detects the operating system and returns the correct Minecraft folder path."""
    system = platform.system()
    home = os.path.expanduser("~")
    if system == "Windows":
        return os.path.join(os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming")), ".minecraft")
    elif system == "Darwin": # macOS
        return os.path.join(home, "Library", "Application Support", "minecraft")
    else: # Linux
        return os.path.join(home, ".minecraft")

def get_java_path(mc_dir):
    """Attempts to find Java on the system, falling back to Minecraft's bundled Java."""
    if shutil.which("java"):
        return "java"
    
    print("\n[*] Java not found in system PATH. Attempting to find Minecraft's bundled Java...")
    search_dirs =[]
    
    if platform.system() == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            search_dirs.append(os.path.join(local_app_data, "Packages", "Microsoft.4297127D64EC6_8wekyb3d8bbwe", "LocalCache", "Local", "runtime"))
        
        prog_files_x86 = os.environ.get("PROGRAMFILES(X86)", "")
        if prog_files_x86:
            search_dirs.append(os.path.join(prog_files_x86, "Minecraft Launcher", "runtime"))
            
        prog_files = os.environ.get("PROGRAMFILES", "")
        if prog_files:
            search_dirs.append(os.path.join(prog_files, "Minecraft Launcher", "runtime"))
    else:
        search_dirs.append(os.path.join(mc_dir, "runtime"))
        
    for d in search_dirs:
        if os.path.exists(d):
            for root, dirs, files in os.walk(d):
                if platform.system() == "Windows":
                    if "java.exe" in files:
                        return os.path.join(root, "java.exe")
                else:
                    if "java" in files and not "java." in files:
                        path = os.path.join(root, "java")
                        if os.access(path, os.X_OK):
                            return path
    return None

def download_file(url, dest, desc="Downloading"):
    """Downloads a file and displays a simple progress tracker."""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            file_size = int(response.info().get('Content-Length', -1))
            with open(dest, 'wb') as out_file:
                chunk_size = 1024 * 8
                downloaded = 0
                while True:
                    buffer = response.read(chunk_size)
                    if not buffer:
                        break
                    out_file.write(buffer)
                    downloaded += len(buffer)
                    if file_size > 0:
                        percent = int(downloaded * 100 / file_size)
                        sys.stdout.write(f"\r{desc}... {percent}%")
                    else:
                        mb = downloaded / (1024 * 1024)
                        sys.stdout.write(f"\r{desc}... {mb:.2f} MB")
                    sys.stdout.flush()
                print() # Newline when done
    except Exception as e:
        print(f"\n[!] Error downloading {url}: {e}")
        sys.exit(1)

def main():
    print(f"\n=== Starting One-Click Installation for {MODPACK_NAME} ===")
    
    mc_dir = get_minecraft_dir()
    install_dir = os.path.join(mc_dir, "profiles", MODPACK_NAME)
    mods_dir = os.path.join(install_dir, "mods")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        
        # --- 1. NEOFORGE INSTALLATION ---
        neoforge_dir = os.path.join(mc_dir, "versions", LOADER_VERSION_ID)
        if not os.path.exists(neoforge_dir):
            print(f"\n[*] NeoForge {NEOFORGE_VERSION} is not installed. Installing it now...")
            java_path = get_java_path(mc_dir)
            if not java_path:
                print("\n[!] ERROR: Could not find Java on your system!")
                print("Please download and install Java 21 to play modded Minecraft 1.21.1.")
                print("Download link: https://adoptium.net/")
                sys.exit(1)
                
            installer_path = os.path.join(temp_dir, "neoforge_installer.jar")
            download_file(NEOFORGE_INSTALLER_URL, installer_path, desc="Downloading NeoForge Installer")
            
            print("[*] Running NeoForge Installer (this may take a minute)...")
            try:
                # --installClient silently installs the loader without popping up a GUI
                subprocess.run([java_path, "-jar", installer_path, "--installClient"], check=True)
                print("[+] NeoForge installed successfully!")
            except subprocess.CalledProcessError as e:
                print(f"\n[!] Error running the NeoForge installer: {e}")
                print("\nTroubleshooting: Ensure you have launched vanilla Minecraft 1.21.1 at least once!")
                sys.exit(1)
        else:
            print(f"\n[*] NeoForge {NEOFORGE_VERSION} is already installed! Skipping loader installation.")

        # --- 2. MODPACK DOWNLOAD & EXTRACTION ---
        zip_path = os.path.join(temp_dir, "modpack.zip")
        extract_path = os.path.join(temp_dir, "extracted")
        
        print(f"\n[*] Downloading Modpack from GitHub...")
        download_file(GITHUB_ZIP_URL, zip_path, desc="Downloading Mods")
            
        print("[*] Extracting files...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
        except Exception as e:
            print(f"[!] Error extracting modpack: {e}")
            sys.exit(1)
            
        # Find the root folder inside the GitHub zip
        extracted_root = None
        for item in os.listdir(extract_path):
            item_path = os.path.join(extract_path, item)
            if os.path.isdir(item_path):
                extracted_root = item_path
                break
                
        if not extracted_root:
            print("[!] Error: Could not locate the extracted files.")
            sys.exit(1)
            
        # --- 3. MOD INSTALLATION ---
        print("[*] Installing mods and cleaning old files...")
        
        # Clean old folders to prevent conflict with deleted mods from previous updates
        for folder_to_clean in["mods", "config", "defaultconfigs"]:
            path_to_clean = os.path.join(install_dir, folder_to_clean)
            if os.path.exists(path_to_clean):
                shutil.rmtree(path_to_clean)
        os.makedirs(mods_dir, exist_ok=True)

        # Smart copy: Handles both proper repo structures and loose .jar uploads
        for item in os.listdir(extracted_root):
            if item.startswith(".") or item.lower() in["readme.md", "license"]:
                continue
                
            s = os.path.join(extracted_root, item)
            
            if os.path.isfile(s):
                if item.endswith(".jar"):
                    # Loose JAR files go straight to the mods folder
                    shutil.copy2(s, os.path.join(mods_dir, item))
                else:
                    # Other loose files (options.txt) go to the profile root
                    shutil.copy2(s, os.path.join(install_dir, item))
            elif os.path.isdir(s):
                d = os.path.join(install_dir, item)
                if os.path.exists(d):
                    for root, dirs, files in os.walk(s):
                        rel_path = os.path.relpath(root, s)
                        target_dir = os.path.join(d, rel_path)
                        os.makedirs(target_dir, exist_ok=True)
                        for file in files:
                            shutil.copy2(os.path.join(root, file), os.path.join(target_dir, file))
                else:
                    shutil.copytree(s, d)

    # --- 4. LAUNCHER PROFILE CONFIGURATION ---
    profiles_path = os.path.join(mc_dir, "launcher_profiles.json")
    if os.path.exists(profiles_path):
        print("\n[*] Configuring Minecraft Launcher...")
        try:
            with open(profiles_path, 'r', encoding='utf-8') as f:
                profiles_data = json.load(f)
                
            profile_id = ''.join(e for e in MODPACK_NAME if e.isalnum())
            now_str = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            new_profile = {
                "name": MODPACK_NAME,
                "type": "custom",
                "created": now_str,
                "lastUsed": now_str,
                "icon": "Furnace",
                "lastVersionId": LOADER_VERSION_ID,
                "gameDir": install_dir
            }
            
            if "profiles" not in profiles_data:
                profiles_data["profiles"] = {}
                
            profiles_data["profiles"][profile_id] = new_profile
            
            with open(profiles_path, 'w', encoding='utf-8') as f:
                json.dump(profiles_data, f, indent=2)
                
            print("[+] Profile successfully added to the Launcher!")
        except Exception as e:
            print(f"[!] Error updating launcher profiles: {e}")
    else:
        print("\n[!] launcher_profiles.json not found! Please run the vanilla Minecraft launcher at least once.")

    print("\n==========================================")
    print("      INSTALLATION COMPLETE!      ")
    print("==========================================")
    print("You can now open the Minecraft Launcher, select")
    print(f"the '{MODPACK_NAME}' profile, and click Play!\n")

if __name__ == "__main__":
    main()
    input("Press Enter to exit...")