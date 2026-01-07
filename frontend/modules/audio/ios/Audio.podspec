Pod::Spec.new do |s|
  s.name           = 'Audio'
  s.version        = '1.0.0'
  s.summary        = 'Native audio module for voice recording and playback'
  s.description    = 'This native module provides streaming audio recording and playback capabilities for voice input/output'
  s.author         = ''
  s.homepage       = 'https://example.com'
  s.platforms      = {
    :ios => '16.0'
  }
  s.source         = { git: '' }
  s.static_framework = true

  s.dependency 'ExpoModulesCore'

  s.pod_target_xcconfig = {
    'DEFINES_MODULE' => 'YES',
  }

  s.source_files = "**/*.swift"
end
