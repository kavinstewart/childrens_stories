Pod::Spec.new do |s|
  s.name           = 'Audio'
  s.version        = '1.0.0'
  s.summary        = 'Native audio module for EVI integration'
  s.description    = 'This native module provides streaming audio recording and playback capabilities for communicating with EVI, the empathic voice interface from Hume AI'
  s.author         = ''
  s.homepage       = 'https://hume.ai'
  s.platforms      = {
    :ios => '16.0'
  }
  s.source         = { git: '' }
  s.static_framework = true

  s.dependency 'ExpoModulesCore'
  s.dependency 'Hume', '0.0.1-beta5'

  s.pod_target_xcconfig = {
    'DEFINES_MODULE' => 'YES',
    'SWIFT_INCLUDE_PATHS' => '$(PODS_TARGET_SRCROOT)',
  }

  s.source_files = "**/*.{h,m,mm,swift,hpp,cpp}"
  s.preserve_paths = 'module.modulemap'
end
