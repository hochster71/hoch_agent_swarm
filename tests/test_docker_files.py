import os
import yaml

def test_docker_files_exist():
    assert os.path.exists("Dockerfile")
    assert os.path.exists("Dockerfile.screenshot")
    assert os.path.exists("docker-compose.yml")
    assert os.path.exists(".dockerignore")

def test_scripts_exist_and_are_executable():
    required_scripts = [
        "scripts/docker_up.sh",
        "scripts/docker_down.sh",
        "scripts/docker_test.sh",
        "scripts/docker_capture_screenshots.sh",
        "scripts/capture_live_screenshots.py"
    ]
    for script in required_scripts:
        assert os.path.exists(script), f"Script missing: {script}"
        if script.endswith(".sh"):
            assert os.access(script, os.X_OK), f"{script} is not executable"

def test_docker_compose_structure():
    with open("docker-compose.yml", "r") as f:
        compose = yaml.safe_load(f)
    
    services = compose.get("services", {})
    assert "hoch-app" in services
    assert "screenshot-worker" in services
    assert "test-runner" in services
    
    # Check port exposure
    ports = services["hoch-app"].get("ports", [])
    assert "8086:8086" in ports
    
    # Check mounts
    volumes = services["hoch-app"].get("volumes", [])
    vol_paths = [v.split(":")[0] for v in volumes]
    assert "./artifacts" in vol_paths
    assert "./data" in vol_paths
