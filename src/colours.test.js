import { describe, it, expect } from 'vitest'
import { getBand, bandStyle, BANDS } from './colours.js'

describe('getBand', () => {
  describe('grey — no data', () => {
    it('returns grey for null median', () => {
      expect(getBand(null, 300000)).toBe('grey')
    })

    it('returns grey for undefined median', () => {
      expect(getBand(undefined, 300000)).toBe('grey')
    })

    it('returns grey for zero median', () => {
      expect(getBand(0, 300000)).toBe('grey')
    })

    it('returns grey for negative median', () => {
      expect(getBand(-1, 300000)).toBe('grey')
    })
  })

  describe('green — median ≤ 95% of budget', () => {
    it('returns green when median is well below budget', () => {
      expect(getBand(200000, 300000)).toBe('green')
    })

    it('returns green when median is exactly 95% of budget', () => {
      expect(getBand(285000, 300000)).toBe('green') // 285000/300000 = 0.95
    })

    it('returns green when median equals budget (ratio = 1 → wait, 1 > 0.95, so amber)', () => {
      // 300000/300000 = 1.0 which is in the amber band
      expect(getBand(300000, 300000)).toBe('amber')
    })
  })

  describe('amber — 95%–115% of budget', () => {
    it('returns amber when just above 95% threshold', () => {
      // 285001/300000 ≈ 0.9500033, just above 0.95
      expect(getBand(285001, 300000)).toBe('amber')
    })

    it('returns amber when median equals budget', () => {
      expect(getBand(300000, 300000)).toBe('amber') // ratio = 1.0
    })

    it('returns amber when median is exactly 115% of budget', () => {
      expect(getBand(345000, 300000)).toBe('amber') // 345000/300000 = 1.15
    })
  })

  describe('red — median > 115% of budget', () => {
    it('returns red when just above 115% threshold', () => {
      expect(getBand(345001, 300000)).toBe('red')
    })

    it('returns red when median is well above budget', () => {
      expect(getBand(600000, 300000)).toBe('red')
    })
  })

  describe('budget edge cases', () => {
    it('handles very small budget', () => {
      expect(getBand(50000, 50000)).toBe('amber') // ratio = 1.0
    })

    it('handles very large budget', () => {
      expect(getBand(100000, 10000000)).toBe('green')
    })
  })
})

describe('bandStyle', () => {
  it('returns correct shape for green', () => {
    const style = bandStyle('green')
    expect(style).toEqual({
      fillColor: BANDS.green.fill,
      color: BANDS.green.stroke,
      weight: 1,
      fillOpacity: 0.65,
    })
  })

  it('returns correct shape for amber', () => {
    const style = bandStyle('amber')
    expect(style).toEqual({
      fillColor: BANDS.amber.fill,
      color: BANDS.amber.stroke,
      weight: 1,
      fillOpacity: 0.65,
    })
  })

  it('returns correct shape for red', () => {
    const style = bandStyle('red')
    expect(style).toEqual({
      fillColor: BANDS.red.fill,
      color: BANDS.red.stroke,
      weight: 1,
      fillOpacity: 0.65,
    })
  })

  it('returns correct shape for grey', () => {
    const style = bandStyle('grey')
    expect(style).toEqual({
      fillColor: BANDS.grey.fill,
      color: BANDS.grey.stroke,
      weight: 1,
      fillOpacity: 0.65,
    })
  })

  it('always has weight 1 and fillOpacity 0.65', () => {
    for (const band of ['green', 'amber', 'red', 'grey']) {
      const style = bandStyle(band)
      expect(style.weight).toBe(1)
      expect(style.fillOpacity).toBe(0.65)
    }
  })
})

describe('BANDS constants', () => {
  it('defines all four bands', () => {
    expect(Object.keys(BANDS)).toEqual(['green', 'amber', 'red', 'grey'])
  })

  it('each band has fill, stroke, and label', () => {
    for (const band of Object.values(BANDS)) {
      expect(band).toHaveProperty('fill')
      expect(band).toHaveProperty('stroke')
      expect(band).toHaveProperty('label')
    }
  })
})
