import { describe, it, expect } from 'vitest'
import { sparklineSVG } from './sparkline.js'

describe('sparklineSVG', () => {
  describe('early returns for insufficient data', () => {
    it('returns empty string for null', () => {
      expect(sparklineSVG(null)).toBe('')
    })

    it('returns empty string for empty array', () => {
      expect(sparklineSVG([])).toBe('')
    })

    it('returns empty string for single value', () => {
      expect(sparklineSVG([200000])).toBe('')
    })

    it('returns empty string when all values are null', () => {
      expect(sparklineSVG([null, null, null])).toBe('')
    })

    it('returns empty string when all values are zero or negative', () => {
      expect(sparklineSVG([0, -1, 0])).toBe('')
    })

    it('filters out null values and returns empty if < 2 remain', () => {
      expect(sparklineSVG([null, 200000, null])).toBe('')
    })
  })

  describe('returns SVG for valid data', () => {
    it('returns an SVG string for two values', () => {
      const result = sparklineSVG([200000, 210000])
      expect(result).toContain('<svg')
      expect(result).toContain('</svg>')
      expect(result).toContain('<polyline')
    })

    it('uses default width and height', () => {
      const result = sparklineSVG([200000, 210000])
      expect(result).toContain('width="120"')
      expect(result).toContain('height="32"')
    })

    it('respects custom width and height', () => {
      const result = sparklineSVG([200000, 210000], 80, 20)
      expect(result).toContain('width="80"')
      expect(result).toContain('height="20"')
    })

    it('sets viewBox matching width and height', () => {
      const result = sparklineSVG([200000, 210000], 80, 20)
      expect(result).toContain('viewBox="0 0 80 20"')
    })
  })

  describe('trend colour', () => {
    it('uses green when last value >= first value (rising)', () => {
      const result = sparklineSVG([200000, 210000])
      expect(result).toContain('stroke="#4ade80"')
    })

    it('uses green when last value equals first value (flat)', () => {
      const result = sparklineSVG([200000, 200000, 200000])
      expect(result).toContain('stroke="#4ade80"')
    })

    it('uses red when last value < first value (falling)', () => {
      const result = sparklineSVG([210000, 200000])
      expect(result).toContain('stroke="#f87171"')
    })
  })

  describe('point coordinates', () => {
    it('first x is 0.0 and last x equals width', () => {
      const result = sparklineSVG([100, 200, 300], 120, 32)
      // First point starts at x=0
      expect(result).toContain('0.0,')
      // Last point ends at x=120
      expect(result).toContain('120.0,')
    })

    it('handles flat data without dividing by zero (range = 0)', () => {
      // All values identical — range = 0, should fall back to range = 1
      expect(() => sparklineSVG([300000, 300000, 300000])).not.toThrow()
      const result = sparklineSVG([300000, 300000, 300000])
      expect(result).toContain('<polyline')
    })
  })

  describe('SVG structure', () => {
    it('includes aria-hidden for accessibility', () => {
      const result = sparklineSVG([200000, 210000])
      expect(result).toContain('aria-hidden="true"')
    })

    it('uses round line joins and caps', () => {
      const result = sparklineSVG([200000, 210000])
      expect(result).toContain('stroke-linejoin="round"')
      expect(result).toContain('stroke-linecap="round"')
    })

    it('has no fill on polyline', () => {
      const result = sparklineSVG([200000, 210000])
      expect(result).toContain('fill="none"')
    })
  })
})
