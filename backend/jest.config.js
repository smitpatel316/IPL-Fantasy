module.exports = {
  testEnvironment: 'node',
  coverageDirectory: 'coverage',
  collectCoverageFrom: [
    'src/**/*.js',
    '!src/db/*.js',
    '!src/index.js'
  ],
  testMatch: [
    '**/tests/unit.test.js'
  ],
  verbose: true,
  testPathIgnorePatterns: ['/node_modules/', 'api.test.js']
};
