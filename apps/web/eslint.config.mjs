import nextVitalsModule from 'eslint-config-next/core-web-vitals.js';

const nextVitals = nextVitalsModule.default ?? nextVitalsModule;
const eslintConfig = Array.isArray(nextVitals) ? nextVitals : [nextVitals];

export default eslintConfig;
