const { join } = require('path');

exports.config = {
  user: process.env.APPIUM_USERNAME || '',
  key: process.env.APPIUM_ACCESS_KEY || '',
  specs: ['./appium.test.js'],
  exclude: [],
  maxInstances: 1,
  capabilities: [{
    platformName: 'iOS',
    platformVersion: '17.0',
    deviceName: 'iPhone 15',
    app: join(__dirname, '../ios/build/IPLFantasyPro.app'),
    automationName: 'XCUITest',
    'appium:screenshotDelay': 5,
    'appium:video': 'true',
    'appium:videoType': 'libx264',
    'appium:videoQuality': 'high',
    'appium:videoFps': 30,
    'appium:videoDir': join(__dirname, 'test-results/videos'),
    'appium:timeLimit': 300,
  }],
  logLevel: 'info',
  bail: 0,
  waitforTimeout: 10000,
  connectionRetryTimeout: 120000,
  connectionRetryCount: 3,
  framework: 'jasmine',
  jasmineNodeOpts: {
    defaultTimeoutInterval: 60000,
  },
  reporters: ['spec'],
  services: [
    ['appium', {
      command: 'appium',
      args: {
        allowCors: true,
        defaultCapabilities: {
          platformName: 'iOS',
          automationName: 'XCUITest'
        }
      }
    }]
  ],
  // Hooks for recording
  before: function(capabilities, specs) {
    console.log('Starting test recording...');
  },
  afterTest: async function(test, context, { error, result, duration, passed, retries }) {
    // Take screenshot on failure
    if (error) {
      console.log('Test failed, capturing screenshot...');
      // Driver screenshot would be captured here
    }
  },
  onComplete: function(exitCode, config, capabilities, results) {
    console.log('Tests completed. Videos saved to test-results/videos/');
  }
};
