import { FrameworkSummary } from "./complianceTypes";

export const FRAMEWORKS: FrameworkSummary[] = [
  {
    id: "nist-csf-2.0",
    name: "NIST CSF 2.0",
    description: "Cybersecurity Framework organizing outcomes around Govern, Identify, Protect, Detect, Respond, and Recover.",
    total_controls: 12,
    implemented_controls: 9,
    partial_controls: 2,
    coverage_percent: 83
  },
  {
    id: "nist-800-53",
    name: "NIST SP 800-53 Rev 5",
    description: "Security and Privacy Controls for Information Systems and Organizations (FedRAMP baseline).",
    total_controls: 18,
    implemented_controls: 13,
    partial_controls: 3,
    coverage_percent: 80
  },
  {
    id: "iso-42001",
    name: "ISO/IEC 42001:2023",
    description: "International Standard specifying requirements for establishing and improving an AI Management System.",
    total_controls: 10,
    implemented_controls: 7,
    partial_controls: 2,
    coverage_percent: 80
  },
  {
    id: "soc2",
    name: "SOC 2 Type II",
    description: "Trust Services Criteria covering Security, Availability, Processing Integrity, Confidentiality, and Privacy.",
    total_controls: 15,
    implemented_controls: 12,
    partial_controls: 2,
    coverage_percent: 86
  }
];
