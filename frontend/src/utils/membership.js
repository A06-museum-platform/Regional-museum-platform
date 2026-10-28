/** "2 adults + 3 children" — the whole of the household model, in words. */
export const coverageLabel = ({ adults_covered: adults, children_covered: children }) => {
  const a = `${adults} ${adults === 1 ? 'adult' : 'adults'}`;
  if (!children) return a;
  return `${a} + ${children} ${children === 1 ? 'child' : 'children'}`;
};
