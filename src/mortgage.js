export function initMortgageCalc(onUpdate) {
  ['deposit', 'term', 'rate'].forEach((id) => {
    document.getElementById(id).addEventListener('input', onUpdate);
  });
}
