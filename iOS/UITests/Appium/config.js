const { join } = require('path');

const androidCaps = {
  platformName: 'Android',
  platformVersion: '14',
  deviceName: 'Pixel 8',
  app: join(__dirname, '../android/build/app.apk'),
  automationName: 'UiAutomator2',
  browserName: '',
  udid: 'auto',
  noReset: false,
  fullReset: true,
  newCommandTimeout: 300,
};

const iosCaps = {
  platformName: 'iOS',
  platformVersion: '17.0',
  deviceName: 'iPhone 15',
  app: join(__dirname, '../ios/build/IPLFantasyPro.app'),
  automationName: 'XCUITest',
  browserName: '',
  udid: 'auto',
  noReset: false,
  fullReset: true,
  newCommandTimeout: 300,
  permissions: JSON.stringify({
    'IPL Fantasy Pro': {
      'Notifications': 'YES',
      'Calendars': 'YES'
    }
  }),
};

const androidLocalCaps = {
  ...androidCaps,
  app: join(__dirname, '../../android/app/build/outputs/apk/debug/app-debug.apk'),
};

const iosSimulatorCaps = {
  platformName: 'iOS',
  platformVersion: '17.0',
  deviceName: 'iPhone 15 Simulator',
  app: join(__dirname, '../../iOS/build/Simulator/IPLFantasyPro.app'),
  automationName: 'XCUITest',
  browserName: '',
  noReset: true,
  newCommandTimeout: 300,
};

function getCaps() {
  const env = process.env.TEST_ENV || 'local';
  const platform = process.env.PLATFORM || 'ios';

  switch (env) {
    case 'android':
      return androidCaps;
    case 'android-local':
      return androidLocalCaps;
    case 'ios-simulator':
      return iosSimulatorCaps;
    case 'cloud':
      // Add cloud provider caps (BrowserStack, Sauce Labs, etc.)
      return platform === 'android' ? androidCaps : iosCaps;
    default:
      return platform === 'android' ? androidCaps : iosCaps;
  }
}

module.exports = {
  getCaps,
  androidCaps,
  iosCaps,
  androidLocalCaps,
  iosSimulatorCaps,
};
