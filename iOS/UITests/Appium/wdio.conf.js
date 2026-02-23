const { join } = require('path');
const { getCaps } = require('./config');

exports.config = {
  user: process.env.APPIUM_USERNAME || '',
  key: process.env.APPIUM_ACCESS_KEY || '',
  specs: [
    './appium.test.js'
  ],
  exclude: [],
  maxInstances: 1,
  capabilities: [getCaps()],
  logLevel: 'info',
  bail: 0,
  waitforTimeout: 10000,
  connectionRetryTimeout: 120000,
  connectionRetryCount: 3,
  framework: 'jasmine',
  jasmineNodeOpts: {
    defaultTimeoutInterval: 60000,
    expectationResultHandler: function (passed, assertion) {
      // Custom handler
    }
  },
  reporters: ['spec'],
  services: [
    [
      'appium',
      {
        command: 'appium',
        args: {
          allowCors: true,
          defaultCapabilities: {
            platformName: 'iOS',
            automationName: 'XCUITest'
          }
        },
        installApp: true,
        cacheInstalledApps: true
      }
    ]
  ],
  before: function (capabilities, specs) {
    console.log('Starting iOS E2E Tests...');
  },
  after: function (exitCode, config, capabilities, results) {
    console.log('Tests completed');
  },
  onPrepare: function (config, capabilities) {
    console.log('Preparing test environment...');
  }
};
