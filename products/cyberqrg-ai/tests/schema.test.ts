import { mockControls, mockRisks } from '../src/data/mockData';

describe('CyberQRG Data Model Schema Tests', () => {
  it('should validate mock control requirements', () => {
    expect(mockControls.length).toBeGreaterThan(0);
    expect(mockControls[0].id).toBe('AC-1');
  });

  it('should validate mock risk records', () => {
    expect(mockRisks.length).toBeGreaterThan(0);
    expect(mockRisks[0].status).toBe('MITIGATED');
  });
});
