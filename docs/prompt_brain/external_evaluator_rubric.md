# HOCH Prompt Brain External Evaluator Rubric

This rubric is designed for external third-party human evaluators (e.g., SCA, ISSO, ISSM, or AO) to verify and audit Prompt Brain outputs across 10 evaluation dimensions.

---

## 1. Evaluation Dimensions

### 1. Correctness (1-10)
* **Score 9-10**: Output is technically and factually correct with zero compliance errors.
* **Score 7-8**: Output has minor formatting issues but is technically correct.
* **Score 1-6**: Critical factual errors or incorrect security control application.

### 2. Evidence Traceability (1-10)
* **Score 9-10**: Every finding is backed by explicit citations from the uploaded evidence.
* **Score 1-6**: Findings are asserted without trace paths or references.

### 3. RMF Alignment (1-10)
* **Score 9-10**: Outputs map precisely to NIST SP 800-53 R5 and NIST SP 800-37 R2 tasks.
* **Score 1-6**: Incorrect or outdated control mapping descriptions.

### 4. Risk Judgment (1-10)
* **Score 9-10**: Identifies and prioritizes risks correctly based on technical severity.
* **Score 1-6**: Minimizes high-severity findings or over-inflates trivial gaps.

### 5. Actionability (1-10)
* **Score 9-10**: Remediations are clear, concrete, and implementable.
* **Score 1-6**: Remediations are vague (e.g., "be secure").

### 6. Hallucination Avoidance (1-10)
* **Score 9-10**: Zero fabricated hostnames, IP addresses, dates, or findings.
* **Score 1-6**: Any fabricated/assumed details found.

### 7. Boundary Awareness (1-10)
* **Score 9-10**: Explicitly states when findings or components fall outside system boundaries.
* **Score 1-6**: Conflates external services with internal control responsibilities.

### 8. Audit Usefulness (1-10)
* **Score 9-10**: High value for compliance auditors compiling evidence logs.
* **Score 1-6**: Low-quality reports that require manual rewriting.

### 9. Executive Usefulness (1-10)
* **Score 9-10**: Recommends human decision points and clear summaries for authorizing officials.
* **Score 1-6**: Dense jargon with no clear executive recommendations.

### 10. Overall Trust (1-10)
* **Score 9-10**: Reviewer has absolute confidence in using this output for compliance packages.
* **Score 1-6**: High risk of compliance failure if output is used.
