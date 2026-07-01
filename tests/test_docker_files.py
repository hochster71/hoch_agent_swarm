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
    assert "has-api" in services
    assert "has-ui" in services
    assert "has-worker" in services
    assert "has-tools" in services
    assert "has-proxy" in services
    
    # Check port exposure
    ports = services["has-ui"].get("ports", [])
    assert "127.0.0.1:8080:8080" in ports
    
    # Check mounts
    volumes = services["has-api"].get("volumes", [])
    vol_paths = []
    for v in volumes:
        if isinstance(v, str):
            vol_paths.append(v.split(":")[0])
        elif isinstance(v, dict) and "source" in v:
            vol_paths.append(v["source"])
            
    assert "./artifacts" in vol_paths
    assert "./backend" in vol_paths
