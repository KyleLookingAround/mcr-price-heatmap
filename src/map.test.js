import { describe, it, expect, vi, beforeAll } from 'vitest'

// Leaflet tries to access the DOM on import. Stub it out before importing map.js.
vi.mock('leaflet', () => ({
  default: {
    map: vi.fn(),
    tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
    geoJSON: vi.fn(() => ({ addTo: vi.fn() })),
    Icon: { Default: { prototype: { _getIconUrl: vi.fn() }, mergeOptions: vi.fn() } },
  },
}))

// Also stub the PNG imports Leaflet expects
vi.mock('leaflet/dist/images/marker-icon.png', () => ({ default: '' }))
vi.mock('leaflet/dist/images/marker-icon-2x.png', () => ({ default: '' }))
vi.mock('leaflet/dist/images/marker-shadow.png', () => ({ default: '' }))

const { getDistrict } = await import('./map.js')

describe('getDistrict', () => {
  it('uses the "name" property when present', () => {
    const feature = { properties: { name: 'M20' } }
    expect(getDistrict(feature)).toBe('M20')
  })

  it('falls back to "postcodes" when name is absent', () => {
    const feature = { properties: { postcodes: 'sk4' } }
    expect(getDistrict(feature)).toBe('SK4')
  })

  it('falls back to "PostDist" when name and postcodes are absent', () => {
    const feature = { properties: { PostDist: 'ol1' } }
    expect(getDistrict(feature)).toBe('OL1')
  })

  it('returns empty string when no known property is present', () => {
    const feature = { properties: {} }
    expect(getDistrict(feature)).toBe('')
  })

  it('uppercases the result', () => {
    const feature = { properties: { name: 'm14' } }
    expect(getDistrict(feature)).toBe('M14')
  })

  it('trims whitespace', () => {
    const feature = { properties: { name: '  BL1  ' } }
    expect(getDistrict(feature)).toBe('BL1')
  })

  it('gives name priority over postcodes', () => {
    const feature = { properties: { name: 'M1', postcodes: 'M2', PostDist: 'M3' } }
    expect(getDistrict(feature)).toBe('M1')
  })

  it('gives postcodes priority over PostDist', () => {
    const feature = { properties: { postcodes: 'M2', PostDist: 'M3' } }
    expect(getDistrict(feature)).toBe('M2')
  })
})
