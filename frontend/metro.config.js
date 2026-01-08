// Learn more https://docs.expo.io/guides/customizing-metro
const { getDefaultConfig } = require('expo/metro-config');
const { withNativeWind } = require('nativewind/metro');

/** @type {import('expo/metro-config').MetroConfig} */
const config = getDefaultConfig(__dirname);

// Add mjs support for ESM modules
config.resolver.sourceExts.push('mjs');

module.exports = withNativeWind(config, { input: './global.css' });
