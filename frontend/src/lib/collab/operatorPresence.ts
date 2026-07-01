import type { OperatorPresence } from "./collaborationTypes";

export const isOperatorActive = (operator: OperatorPresence, timeoutMs: number = 300000): boolean => {
  if (operator.status !== "online") return false;
  const lastActiveTime = new Date(operator.last_active).getTime();
  return Date.now() - lastActiveTime < timeoutMs;
};

export const getOnlineOperators = (operators: OperatorPresence[]): OperatorPresence[] => {
  return operators.filter((op) => op.status === "online" || op.status === "away");
};

export const canFulfillRole = (
  operators: OperatorPresence[],
  requiredRole: "approver" | "admin"
): boolean => {
  return operators.some(
    (op) =>
      (op.status === "online" || op.status === "away") &&
      (requiredRole === "approver" ? op.role === "approver" || op.role === "admin" : op.role === "admin")
  );
};
