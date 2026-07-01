#!/usr/bin/env python3
# scripts/epic_fury_csp_audit.py — Content Security Policy static audit tool for Epic Fury 2026
import sys
import re

def audit_file(file_path):
    print(f"Auditing CSP in: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify buildCSP function is present
    if "function buildCSP(" not in content:
        print(f"  [FAIL] buildCSP function not found in {file_path}")
        return False

    # Check isPreviewOrDev detection logic
    if "process.env.VERCEL_ENV" not in content:
        print(f"  [FAIL] process.env.VERCEL_ENV check is missing from {file_path}")
        return False

    # Find buildCSP list return elements
    # Since it returns an array of strings joined by '; ', we can extract the return array.
    match = re.search(r'return\s*\[(.*?)\]\.join', content, re.DOTALL)
    if not match:
        print(f"  [FAIL] buildCSP return statement not found or malformed in {file_path}")
        return False
    
    csp_lines_raw = match.group(1).split(",")
    csp_directives = []
    for line in csp_lines_raw:
        line_clean = line.strip().strip('"').strip("'").strip('`').strip()
        if line_clean:
            csp_directives.append(line_clean)

    # Required directives
    required_directives = [
        "frame-src", "script-src", "connect-src", "img-src", 
        "style-src", "font-src", "frame-ancestors", "report-uri"
    ]
    
    directives_found = {}
    for d in required_directives:
        found = False
        for line in csp_directives:
            if line.startswith(d) or f"{d} " in line or (d == "script-src" and "scriptSrc" in line) or (d == "frame-src" and "frameSrc" in line):
                found = True
                directives_found[d] = line
                break
        if not found:
            print(f"  [FAIL] Missing required CSP directive '{d}' in {file_path}")
            return False
        else:
            print(f"  [PASS] Directive '{d}' is configured: {directives_found[d]}")

    # Verify frame-src is correctly configured for both environments
    match_frame_src = re.search(r'frameSrc\s*=\s*isPreviewOrDev\s*\?\s*(["\'`])(.*?)\1\s*:\s*(["\'`])(.*?)\3', content)
    if match_frame_src:
        prev_val = match_frame_src.group(2)
        prod_val = match_frame_src.group(4)
        
        # Audit Production
        print(f"  [INFO] Extracted production frame-src: '{prod_val}'")
        if "vercel.live" in prod_val:
            print(f"  [FAIL] Production frame-src allows vercel.live! Violation of production hardening.")
            return False
        if "https://js.stripe.com" not in prod_val or "https://hooks.stripe.com" not in prod_val:
            print(f"  [FAIL] Production frame-src does not keep Stripe origins intact!")
            return False
        print(f"  [PASS] Production frame-src is hardened and keeps Stripe origins intact.")

        # Audit Preview
        print(f"  [INFO] Extracted preview frame-src: '{prev_val}'")
        if "vercel.live" not in prev_val:
            print(f"  [FAIL] Preview frame-src does not allow vercel.live!")
            return False
        if "https://js.stripe.com" not in prev_val or "https://hooks.stripe.com" not in prev_val:
            print(f"  [FAIL] Preview frame-src does not keep Stripe origins intact!")
            return False
        print(f"  [PASS] Preview frame-src correctly allows vercel.live.")
    else:
        print(f"  [FAIL] Could not verify frame-src configuration in {file_path}")
        return False

    print(f"  [PASS] CSP Audit passed for {file_path}\n")
    return True

def main():
    files = [
        "/Users/michaelhoch/Downloads/Epic-fury-2026-main/middleware.ts",
        "/Users/michaelhoch/epic-fury-build/epic-fury-2026/middleware.ts"
    ]
    all_pass = True
    for f in files:
        if not audit_file(f):
            all_pass = False
    
    if not all_pass:
        sys.exit(1)
    else:
        print("==================================================")
        print(">> SUCCESS: ALL CSP AUDITS PASS!")
        print("==================================================")

if __name__ == "__main__":
    main()
