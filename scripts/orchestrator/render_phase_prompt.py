#!/usr/bin/env python3
import sys
import os
import json
import glob

def render_prompt(next_phase):
    print(f"[render_phase_prompt] Finding template for phase {next_phase}...")
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    templates_dir = os.path.join(base_dir, "templates/phases")
    
    pattern = os.path.join(templates_dir, f"{next_phase}-*.md")
    matching_files = glob.glob(pattern)
    
    if not matching_files:
        # Try finding template named just {next_phase}.md
        pattern_exact = os.path.join(templates_dir, f"{next_phase}.md")
        if os.path.exists(pattern_exact):
            matching_files = [pattern_exact]
        else:
            print(f"[render_phase_prompt] FAIL: No template file found matching pattern {pattern}")
            sys.exit(1)
            
    template_path = matching_files[0]
    print(f"[render_phase_prompt] Loading template: {os.path.basename(template_path)}")
    with open(template_path, "r") as f:
        template_content = f.read()

    # Load registry and state to interpolate or append variables
    registry_path = os.path.join(base_dir, "control/phase_registry.json")
    state_path = os.path.join(base_dir, "control/phase_state.json")
    
    with open(registry_path, "r") as f:
        registry = json.load(f)
    with open(state_path, "r") as f:
        state = json.load(f)

    # Append runtime enforcement info to the template prompt
    enforcement_appendix = f"\n\n## Orchestrator Runtime Attestation\n" \
                           f"- Current Integration Branch: {state.get('current_branch_expected')}\n" \
                           f"- Expected Staging Tag: {registry.get('current_track')}14-staging\n" \
                           f"- Autonomous Operations Restricted: Yes (local dev sandbox only)\n" \
                           f"- Blocked Actions: git push, main merge, production deploy, secrets\n"

    rendered_content = template_content + enforcement_appendix
    
    output_dir = os.path.join(base_dir, "artifacts/orchestrator/generated-prompts")
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"{next_phase}.md")
    with open(output_file, "w") as f:
        f.write(rendered_content)
        
    print(f"[render_phase_prompt] PASS: Rendered prompt written to {output_file}")
    return output_file, rendered_content

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: render_phase_prompt.py <phase_name>")
        sys.exit(1)
    render_prompt(sys.argv[1])
