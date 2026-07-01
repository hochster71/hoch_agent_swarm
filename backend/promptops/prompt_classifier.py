import re

class PromptClassifier:
    def __init__(self):
        self.rules = {
            "KUBERNETES_LANE": [r"kubernetes", r"k8s", r"k3d", r"helm", r"pod", r"ingress"],
            "DOCKER_RUNTIME": [r"docker", r"container", r"compose", r"daemon", r"socket", r"mount"],
            "TRANSPORT_SECURITY": [r"https", r"http/3", r"tls", r"ssl", r"certificate", r"encryption"],
            "UI_TRUTH_FIX": [r"ui truth", r"fake green", r"stale telemetry", r"cockpit display"],
            "SHOPPING_RESEARCH_GATE": [r"shopping", r"toy", r"purchase block", r"lego", r"price rank"],
            "OPERATOR_HANDOFF": [r"handoff", r"chatgpt interact", r"operator chat", r"console"],
            "SECURITY_HARDENING": [r"vulnerability", r"audit", r"cve", r"red team", r"security scan"],
            "ZERO_DEFECT_CLOSEOUT": [r"zero defect", r"closeout", r"waive finding", r"vulnerabilities count"],
            "ARCHITECTURE_DECISION": [r"architecture", r"framework", r"design decision", r"pert"],
            "EMERGENCY_DEBUG": [r"emergency", r"crash", r"permission denied", r"unresponsive", r"timeout"],
            "FEATURE_GATE": [r"gate", r"rule", r"policy", r"check"],
            "GENERAL_E2E_BUILD": [r"build e2e", r"production ready", r"complete everything", r"no errors"]
        }

    def classify(self, prompt_text: str) -> str:
        prompt_text_lower = prompt_text.lower()
        for category, patterns in self.rules.items():
            for pattern in patterns:
                if re.search(pattern, prompt_text_lower):
                    return category
        return "GENERAL_E2E_BUILD"
