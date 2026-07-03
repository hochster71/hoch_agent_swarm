export const securityPolicy = {
  offlineModeOnly: true,
  allowExternalLookups: false,
  prohibitedDomains: ["*.google-analytics.com", "*.amplitude.com", "*.mixpanel.com"],
  allowSecretStorage: false,
  allowCustomerDataStorage: false,
  releaseBlocked: true,
  authorizedAdapters: ["ollama_gpu_pod", "lmstudio"],
  blockedAdapters: ["ollama_native"]
};

export function checkPolicyCompliance(): boolean {
  if (!securityPolicy.offlineModeOnly) return false;
  if (securityPolicy.allowExternalLookups) return false;
  if (securityPolicy.allowSecretStorage) return false;
  if (securityPolicy.allowCustomerDataStorage) return false;
  return true;
}
