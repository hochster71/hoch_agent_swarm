# HELM AI Agent Governance Discovery Questionnaire
**Ref:** Q-REV-M1-DISCOVERY  

Use this questionnaire during preliminary discovery calls with technical and security stakeholders to scope the AI Agent Governance & Cybersecurity Assessment.

---

## 1. Agent Architecture & Frameworks
* **Q1.1:** What frameworks or libraries are you using to orchestrate your AI agents? (e.g., CrewAI, LangChain, AutoGen, LangGraph, or a custom-built solution?)
* **Q1.2:** Which foundation LLMs are utilized, and how are they hosted? (e.g., OpenAI API, Anthropic API, private cloud endpoints via vLLM, local Ollama/Llama.cpp?)
* **Q1.3:** Are the agents single-step or do they operate in multi-agent loops/swarms with complex feedback paths?

---

## 2. Privileges & Execution Boundaries
* **Q2.1:** What tools or execution capabilities do your agents have access to? (e.g., database read/write, local OS shell execution, web searching, third-party API integration?)
* **Q2.2:** What system privileges do the agent execution containers/processes run under? (e.g., root, non-root service account, Kubernetes service account, local user?)
* **Q2.3:** Are agent network connections restricted? Do they run in isolated VPCs, or do they have unrestricted outbound internet access?

---

## 3. Auditability & Evidence Integrity
* **Q3.1:** How are the actions, prompts, and tool outputs of your agents logged? (e.g., stdout, flat files, central logging like Datadog/Splunk, relational database?)
* **Q3.2:** Do you have a mechanism to verify that an execution log or ledger has not been mutated after the fact?
* **Q3.3:** Can you trace a specific agent action (e.g., a database update) back to a verifiable chain of prompts and model decisions?

---

## 4. Compliance & Certification Context
* **Q4.1:** What security certifications or compliance frameworks is your organization currently subject to or preparing for? (e.g., SOC 2 Type II, HIPAA, ISO 27001, CMMC, NIST SP 800-53/RMF?)
* **Q4.2:** Has a security audit ever flagged your AI/LLM integration as an open finding or high-risk item?
* **Q4.3:** Do your enterprise customers ask for security assessments of your AI features during procurement?

---

## 5. Human-in-the-Loop & Approval Gates
* **Q5.1:** Are there human-in-the-loop (HITL) approval gates before your agents perform high-risk actions? (e.g., executing money transfers, deleting database records, modifying system configs?)
* **Q5.2:** How are these approval decisions logged and bound to the agent's execution context?
* **Q5.3:** Is there a fail-closed policy if the approval gate is unreachable or times out?
