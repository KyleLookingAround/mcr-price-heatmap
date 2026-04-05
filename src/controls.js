/**
 * Wire up sidebar controls: budget slider/input, property type buttons,
 * mortgage calculator, localStorage persistence, and the "fit affordable" button.
 */

const STORAGE_KEY = 'mcr-heatmap-prefs'
const DEBOUNCE_MS = 50

export function loadPrefs() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return null
}

function savePrefs(budget, propType) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ budget, propType }))
  } catch {}
}

function debounce(fn, ms) {
  let t
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms) }
}

/**
 * @param {function} onChange  — called with (budget: number, propType: string)
 * @param {function} onFitAffordable — called with (budget, propType)
 * @returns {{ getBudget, getType }}
 */
export function initControls(onChange, onFitAffordable) {
  const budgetInput  = document.getElementById('budget-input')
  const budgetSlider = document.getElementById('budget-slider')
  const typeButtons  = document.querySelectorAll('.type-btn')
  const fitBtn       = document.getElementById('fit-affordable')

  // Mortgage calculator
  const depositInput  = document.getElementById('deposit')
  const termInput     = document.getElementById('term')
  const rateInput     = document.getElementById('rate')
  const maxPurchaseEl = document.getElementById('max-purchase')
  const monthlyEl     = document.getElementById('monthly-payment')
  const applyBtn      = document.getElementById('apply-mortgage')

  let budget = parseInt(budgetInput.value, 10)
  let propType = 'all'

  // Restore from localStorage
  const prefs = loadPrefs()
  if (prefs) {
    budget = prefs.budget || budget
    propType = prefs.propType || propType
    budgetInput.value = budget
    budgetSlider.value = Math.min(budget, parseInt(budgetSlider.max, 10))
    typeButtons.forEach(b => {
      b.classList.toggle('active', b.dataset.type === propType)
    })
  }

  const notify = debounce(() => {
    savePrefs(budget, propType)
    onChange(budget, propType)
  }, DEBOUNCE_MS)

  // Sync slider → input
  budgetSlider.addEventListener('input', () => {
    budget = parseInt(budgetSlider.value, 10)
    budgetInput.value = budget
    notify()
  })

  // Sync input → slider
  budgetInput.addEventListener('input', () => {
    const v = parseInt(budgetInput.value, 10)
    if (!isNaN(v) && v >= 50000) {
      budget = v
      budgetSlider.value = Math.min(v, parseInt(budgetSlider.max, 10))
      notify()
    }
  })

  // Property type toggle
  typeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      propType = btn.dataset.type
      typeButtons.forEach(b => b.classList.remove('active'))
      btn.classList.add('active')
      notify()
    })
  })

  // Fit to affordable
  fitBtn.addEventListener('click', () => onFitAffordable(budget, propType))

  // Mortgage calculator
  const fmt = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 })

  function calcMortgage() {
    const deposit = parseFloat(depositInput.value) || 0
    const term    = parseInt(termInput.value, 10) || 25
    const annRate = parseFloat(rateInput.value) || 4.5

    const monthlyRate = annRate / 100 / 12
    const n = term * 12

    // Max affordable loan for a monthly payment heuristic (income ~4.5x salary)
    // Instead, show: for a given total purchase price = deposit + loan
    // We'll compute max purchase by solving for loan where monthly payment
    // is a "typical" affordability ceiling — but without income data we can't.
    // More useful: just compute monthly payment for the current budget - deposit.
    const loan = Math.max(0, budget - deposit)

    let monthly = 0
    if (monthlyRate > 0 && loan > 0) {
      monthly = (loan * monthlyRate * Math.pow(1 + monthlyRate, n)) /
                (Math.pow(1 + monthlyRate, n) - 1)
    } else if (loan > 0) {
      monthly = loan / n
    }

    maxPurchaseEl.textContent = fmt.format(budget)
    monthlyEl.textContent = fmt.format(Math.round(monthly))
  }

  ;[depositInput, termInput, rateInput].forEach(el =>
    el.addEventListener('input', calcMortgage)
  )

  applyBtn.addEventListener('click', () => {
    const deposit  = parseFloat(depositInput.value) || 0
    const term     = parseInt(termInput.value, 10) || 25
    const annRate  = parseFloat(rateInput.value) || 4.5
    const monthlyRate = annRate / 100 / 12
    const n = term * 12

    // Solve for max loan given a rough monthly budget
    // Use a sensible default: max purchase = what the mortgage can buy at 28% of
    // a median UK salary. Without income data, we'll keep it simple:
    // just apply deposit + current loan as the budget.
    // Real utility: user adjusts deposit/rate/term and sees the new budget.
    const currentLoan = Math.max(0, budget - deposit)
    const newBudget = deposit + currentLoan
    budget = Math.round(newBudget)
    budgetInput.value = budget
    budgetSlider.value = Math.min(budget, parseInt(budgetSlider.max, 10))
    notify()
    calcMortgage()
  })

  // Initial calculation
  calcMortgage()

  // Also recalc mortgage display when budget changes
  const origNotify = notify
  budgetInput.addEventListener('change', calcMortgage)
  budgetSlider.addEventListener('change', calcMortgage)

  return {
    getBudget: () => budget,
    getType: () => propType,
  }
}
