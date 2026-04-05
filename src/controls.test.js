import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { calcMortgagePayment, loadPrefs, STORAGE_KEY } from './controls.js'

// ─── calcMortgagePayment ────────────────────────────────────────────────────

describe('calcMortgagePayment', () => {
  describe('zero / negative loan', () => {
    it('returns 0 for zero loan', () => {
      expect(calcMortgagePayment(0, 4.5, 25)).toBe(0)
    })

    it('returns 0 for negative loan', () => {
      expect(calcMortgagePayment(-50000, 4.5, 25)).toBe(0)
    })
  })

  describe('zero interest rate', () => {
    it('divides loan evenly over term months (no interest)', () => {
      // 300000 over 25 years = 300 months → £1000/month
      expect(calcMortgagePayment(300000, 0, 25)).toBeCloseTo(1000, 2)
    })

    it('works with a 10-year term at 0%', () => {
      // 120000 / 120 months = £1000/month
      expect(calcMortgagePayment(120000, 0, 10)).toBeCloseTo(1000, 2)
    })
  })

  describe('standard amortisation formula', () => {
    it('calculates typical repayment correctly', () => {
      // £200k loan, 4.5% annual, 25 years
      // Monthly rate = 0.375%, n = 300
      // Expected ≈ £1111.61/month (industry standard calculators)
      expect(calcMortgagePayment(200000, 4.5, 25)).toBeCloseTo(1111.61, 0)
    })

    it('higher interest rate increases monthly payment', () => {
      const low  = calcMortgagePayment(200000, 2.0, 25)
      const high = calcMortgagePayment(200000, 6.0, 25)
      expect(high).toBeGreaterThan(low)
    })

    it('longer term decreases monthly payment', () => {
      const short = calcMortgagePayment(200000, 4.5, 15)
      const long  = calcMortgagePayment(200000, 4.5, 30)
      expect(long).toBeLessThan(short)
    })

    it('larger loan increases monthly payment proportionally at 0%', () => {
      const small = calcMortgagePayment(100000, 0, 25)
      const large = calcMortgagePayment(200000, 0, 25)
      expect(large).toBeCloseTo(small * 2, 2)
    })

    it('returns a positive number for valid inputs', () => {
      expect(calcMortgagePayment(150000, 3.5, 20)).toBeGreaterThan(0)
    })
  })

  describe('edge cases', () => {
    it('handles very small loan', () => {
      expect(calcMortgagePayment(1, 4.5, 25)).toBeGreaterThan(0)
    })

    it('handles very high interest rate', () => {
      const payment = calcMortgagePayment(100000, 20, 25)
      expect(payment).toBeGreaterThan(0)
      // At 20% annual rate, monthly is very high
      expect(payment).toBeGreaterThan(1600)
    })

    it('handles 1-year term', () => {
      // £12000 at 0% over 1 year = £1000/month
      expect(calcMortgagePayment(12000, 0, 1)).toBeCloseTo(1000, 2)
    })
  })
})

// ─── loadPrefs ──────────────────────────────────────────────────────────────

describe('loadPrefs', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('returns null when nothing is stored', () => {
    expect(loadPrefs()).toBeNull()
  })

  it('returns parsed prefs when valid JSON is stored', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ budget: 400000, propType: 'flat' }))
    const prefs = loadPrefs()
    expect(prefs).toEqual({ budget: 400000, propType: 'flat' })
  })

  it('returns null when stored value is invalid JSON', () => {
    localStorage.setItem(STORAGE_KEY, 'not-json{{{')
    expect(loadPrefs()).toBeNull()
  })

  it('preserves numeric budget', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ budget: 250000, propType: 'all' }))
    expect(loadPrefs().budget).toBe(250000)
  })

  it('preserves propType string', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ budget: 250000, propType: 'semi' }))
    expect(loadPrefs().propType).toBe('semi')
  })

  it('returns prefs object even when budget is missing', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ propType: 'terraced' }))
    const prefs = loadPrefs()
    expect(prefs).not.toBeNull()
    expect(prefs.propType).toBe('terraced')
  })

  it('uses the correct storage key', () => {
    expect(STORAGE_KEY).toBe('mcr-heatmap-prefs')
  })
})
