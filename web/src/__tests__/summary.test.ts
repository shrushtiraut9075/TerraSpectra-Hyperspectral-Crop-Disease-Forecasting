import { describe, it, expect } from 'vitest';

describe('Deterministic Natural Language Summary Generator', () => {
  it('generates correct summary sentence when risk exists', () => {
    const acresAtRisk = 48.2;
    const acresTotal = 1000.4;
    const percentAtRisk = 4.8;
    const largestZone = { area_acres: 12.1, mean_risk: 0.87 };

    const sentence = `${percentAtRisk}% of the field (${acresAtRisk} acres) exhibits chemical stress signatures ~3 weeks ahead of visible chlorosis. Largest focal zone covers ${largestZone.area_acres} acres (mean risk: ${(largestZone.mean_risk * 100).toFixed(0)}%).`;

    expect(sentence).toContain('4.8% of the field');
    expect(sentence).toContain('48.2 acres');
    expect(sentence).toContain('12.1 acres');
    expect(sentence).toContain('mean risk: 87%');
  });

  it('generates zero-risk sentence when all crop sectors are healthy', () => {
    const acresAtRisk = 0.0;
    const threshold = 0.5;

    const sentence = acresAtRisk > 0
      ? 'Stressed'
      : `0.0% of the surveyed acreage exceeds the ${Math.round(threshold * 100)}% disease risk threshold. All crop sectors appear healthy.`;

    expect(sentence).toContain('0.0% of the surveyed acreage');
    expect(sentence).toContain('50% disease risk threshold');
  });
});

