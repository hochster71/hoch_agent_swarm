import { checkPolicyCompliance, securityPolicy } from '../src/security/securityPolicy';

describe('CyberQRG Security Policy Tests', () => {
  it('should enforce offline-only execution', () => {
    expect(securityPolicy.offlineModeOnly).toBe(true);
    expect(checkPolicyCompliance()).toBe(true);
  });

  it('should prevent external lookups', () => {
    expect(securityPolicy.allowExternalLookups).toBe(false);
  });

  it('should restrict heavy routing tasks from native 1.5B', () => {
    expect(securityPolicy.blockedAdapters).toContain('ollama_native');
  });
});
