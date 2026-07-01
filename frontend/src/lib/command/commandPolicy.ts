import type { ParsedCommand } from "./commandTypes";

export function runMockPolicyCheck(command: ParsedCommand) {
  if (command.intent === "unknown") {
    return {
      required: true,
      result: "failed" as const,
      policy_ids: ["POLICY_COMMAND_INTENT_REQUIRED"],
      explanation: "Command intent could not be classified.",
    };
  }
  return {
    required: true,
    result: "passed" as const,
    policy_ids: ["POLICY_OPERATOR_SCOPE_VALID"],
    explanation: "Operator scope permits this command in LOCAL environment.",
  };
}
