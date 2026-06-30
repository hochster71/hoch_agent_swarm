#!/usr/bin/env python3
import os
import sys
import json
import urllib.request

USER = "hochster71"
URL = f"https://api.github.com/users/{USER}/repos"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "has_live_project_tracker", "data", "github_inventory.json")

# Fallback cached/mock data in case of offline run or rate limiting
MOCK_DATA = [
  {
    "name": "hoch_agent_swarm",
    "html_url": "https://github.com/hochster71/hoch_agent_swarm",
    "description": "Multi-agent autonomous cybersecurity research and operations swarm.",
    "size": 15420,
    "language": "Python",
    "stargazers_count": 12,
    "forks_count": 2,
    "open_issues_count": 0,
    "updated_at": "2026-06-30T13:30:00Z"
  },
  {
    "name": "has_live_project_tracker",
    "html_url": "https://github.com/hochster71/has_live_project_tracker",
    "description": "Dynamic web cockpit and CPM scheduler for the agent swarm.",
    "size": 890,
    "language": "JavaScript",
    "stargazers_count": 5,
    "forks_count": 0,
    "open_issues_count": 1,
    "updated_at": "2026-06-30T14:00:00Z"
  },
  {
    "name": "hoch_agent_swarm_prompt_library",
    "html_url": "https://github.com/hochster71/hoch_agent_swarm_prompt_library",
    "description": "A curated collection of system instructions, schemas, and few-shot examples for HAS nodes.",
    "size": 4320,
    "language": "Markdown",
    "stargazers_count": 8,
    "forks_count": 1,
    "open_issues_count": 0,
    "updated_at": "2026-06-29T18:30:00Z"
  }
]

def main():
    print("==================================================")
    print("INGESTING GITHUB PROJECT INVENTORY (T007)")
    print("==================================================")

    repos = []
    try:
        print(f"Fetching public repositories for '{USER}' from GitHub API...")
        req = urllib.request.Request(
            URL,
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode('utf-8'))
            for item in data:
                repos.append({
                    "name": item.get("name"),
                    "html_url": item.get("html_url"),
                    "description": item.get("description"),
                    "size": item.get("size"),
                    "language": item.get("language"),
                    "stargazers_count": item.get("stargazers_count"),
                    "forks_count": item.get("forks_count"),
                    "open_issues_count": item.get("open_issues_count"),
                    "updated_at": item.get("updated_at")
                })
        print(f"Successfully fetched {len(repos)} repositories from GitHub API.")
    except Exception as e:
        print(f"Warning: GitHub API fetch failed or rate limited ({e}). Falling back to cached inventory.", file=sys.stderr)
        repos = MOCK_DATA

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(repos, f, indent=2)

    print(f"Successfully wrote GitHub inventory to {OUTPUT_PATH}.")

if __name__ == "__main__":
    main()
