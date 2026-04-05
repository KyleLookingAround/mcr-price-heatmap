import { describe, it, expect } from 'vitest'
import { buildPopup } from './popup.js'

const DISTRICT = 'M20'
const BUDGET = 300000

const fullData = {
  all: {
    median: 340000,
    count: 412,
    delta12m: 2.1,
    history: Array.from({ length: 36 }, (_, i) => 300000 + i * 1000),
  },
  flat: {
    median: 215000,
    count: 180,
    delta12m: -3.5,
    history: Array.from({ length: 36 }, (_, i) => 200000 + i * 500),
  },
  terraced: {
    median: 355000,
    count: 120,
    delta12m: 0.8,
    history: null,
  },
}

describe('buildPopup', () => {
  describe('structure', () => {
    it('returns a non-empty string', () => {
      const html = buildPopup(DISTRICT, fullData, 'all', BUDGET)
      expect(typeof html).toBe('string')
      expect(html.length).toBeGreaterThan(0)
    })

    it('contains the district code', () => {
      const html = buildPopup(DISTRICT, fullData, 'all', BUDGET)
      expect(html).toContain('M20')
    })

    it('contains the popup-content wrapper', () => {
      const html = buildPopup(DISTRICT, fullData, 'all', BUDGET)
      expect(html).toContain('class="popup-content"')
    })

    it('contains a Rightmove link', () => {
      const html = buildPopup(DISTRICT, fullData, 'all', BUDGET)
      expect(html).toContain('rightmove.co.uk')
      expect(html).toContain('href=')
    })

    it('encodes district in the Rightmove URL', () => {
      const html = buildPopup(DISTRICT, fullData, 'all', BUDGET)
      expect(html).toContain('M20')
    })

    it('includes budget in Rightmove URL', () => {
      const html = buildPopup(DISTRICT, fullData, 'all', BUDGET)
      expect(html).toContain('300000')
    })
  })

  describe('property type labels', () => {
    it('shows "All types" for propType "all"', () => {
      const html = buildPopup(DISTRICT, fullData, 'all', BUDGET)
      expect(html).toContain('All types')
    })

    it('shows "Flats" for propType "flat"', () => {
      const html = buildPopup(DISTRICT, fullData, 'flat', BUDGET)
      expect(html).toContain('Flats')
    })

    it('shows "Terraced" for propType "terraced"', () => {
      const html = buildPopup(DISTRICT, fullData, 'terraced', BUDGET)
      expect(html).toContain('Terraced')
    })

    it('falls back to propType string for unknown type', () => {
      const html = buildPopup(DISTRICT, fullData, 'bungalow', BUDGET)
      expect(html).toContain('bungalow')
    })
  })

  describe('median price display', () => {
    it('formats median price in GBP', () => {
      const html = buildPopup(DISTRICT, fullData, 'all', BUDGET)
      // £340,000 formatted
      expect(html).toContain('340,000')
    })

    it('shows "No data" when median is missing', () => {
      const noMedian = { all: { count: 5, delta12m: null, history: [] } }
      const html = buildPopup(DISTRICT, noMedian, 'all', BUDGET)
      expect(html).toContain('No data')
    })

    it('shows percentage of budget', () => {
      // 340000 / 300000 * 100 = 113%
      const html = buildPopup(DISTRICT, fullData, 'all', BUDGET)
      expect(html).toContain('113%')
      expect(html).toContain('of your budget')
    })

    it('omits percentage label when median is missing', () => {
      const noMedian = { all: { count: 5, delta12m: null, history: [] } }
      const html = buildPopup(DISTRICT, noMedian, 'all', BUDGET)
      expect(html).not.toContain('of your budget')
    })
  })

  describe('sales count display', () => {
    it('shows sales count with label', () => {
      const html = buildPopup(DISTRICT, fullData, 'all', BUDGET)
      expect(html).toContain('412 sales')
    })

    it('shows dash when count is missing', () => {
      const noCount = { all: { median: 300000, delta12m: null, history: [] } }
      const html = buildPopup(DISTRICT, noCount, 'all', BUDGET)
      expect(html).toContain('—')
    })
  })

  describe('trend arrow', () => {
    it('shows up arrow for delta > 2%', () => {
      const html = buildPopup(DISTRICT, fullData, 'all', BUDGET) // delta12m = 2.1
      expect(html).toContain('▲')
      expect(html).toContain('2.1%')
    })

    it('shows down arrow for delta < -2%', () => {
      const html = buildPopup(DISTRICT, fullData, 'flat', BUDGET) // delta12m = -3.5
      expect(html).toContain('▼')
      expect(html).toContain('3.5%')
    })

    it('shows flat arrow for delta between -2% and 2%', () => {
      const html = buildPopup(DISTRICT, fullData, 'terraced', BUDGET) // delta12m = 0.8
      expect(html).toContain('→')
      expect(html).toContain('0.8%')
    })

    it('shows nothing for null delta', () => {
      const noDelta = { all: { median: 300000, count: 100, delta12m: null, history: [] } }
      const html = buildPopup(DISTRICT, noDelta, 'all', BUDGET)
      expect(html).not.toContain('▲')
      expect(html).not.toContain('▼')
      // The Rightmove link text contains →, so check the trend span is absent instead
      expect(html).not.toContain('class="trend')
    })
  })

  describe('sparkline', () => {
    it('includes sparkline section when history is present', () => {
      const html = buildPopup(DISTRICT, fullData, 'all', BUDGET)
      expect(html).toContain('popup-spark')
      expect(html).toContain('36-month price trend')
    })

    it('omits sparkline section when history is missing', () => {
      const noHistory = { all: { median: 300000, count: 100, delta12m: 1.0, history: [] } }
      const html = buildPopup(DISTRICT, noHistory, 'all', BUDGET)
      expect(html).not.toContain('popup-spark')
    })
  })

  describe('propType fallback to all', () => {
    it('uses all data when requested propType has no data', () => {
      // fullData has no 'detached' key — should fall back to all
      const html = buildPopup(DISTRICT, fullData, 'detached', BUDGET)
      // Median from 'all' is 340000
      expect(html).toContain('340,000')
    })
  })

  describe('history fallback', () => {
    it('falls back to all.history when type history is null', () => {
      // terraced has history: null, should fall back to all.history
      const html = buildPopup(DISTRICT, fullData, 'terraced', BUDGET)
      expect(html).toContain('popup-spark')
    })
  })
})
