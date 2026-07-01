import sys
import subprocess
import urllib.request
import json

def check_package(package_name):
    try:
        __import__(package_name)
        print(f"[OK] Package '{package_name}' is installed.")
        return True
    except ImportError:
        print(f"[MISSING] Package '{package_name}' is not installed.")
        return False

def check_ollama():
    url = "http://localhost:11434/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            models = [m["name"] for m in data.get("models", [])]
            print(f"[OK] Ollama is running at http://localhost:11434")
            print(f"     Available models: {models if models else 'None (download models via: ollama pull <model>)'}")
            return True
    except Exception as e:
        print(f"[WARNING] Could not connect to local Ollama (http://localhost:11434): {e}")
        print("          Ensure Ollama is running if you want to use local LLM inference.")
        return False

def install_missing_packages(missing):
    print("\nAttempting to install missing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
        print("[OK] Successfully installed missing dependencies.")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to install packages: {e}")
        return False

def main():
    print("==================================================")
    print("Verifying Hoch Swarm Environment...")
    print("==================================================")

    required_packages = ["fastapi", "uvicorn", "pydantic", "psutil"]
    missing = []
    
    for pkg in required_packages:
        if not check_package(pkg):
            missing.append(pkg)
            
    if missing:
        success = install_missing_packages(missing)
        if not success:
            print("[ERROR] Please install missing packages manually: pip install fastapi uvicorn pydantic psutil")
            sys.exit(1)
            
    print("\nChecking local LLM capabilities...")
    check_ollama()
    
    print("\nEnvironment verification completed.")
    print("==================================================")

if __name__ == "__main__":
    main()
