import AVFoundation
import ExpoModulesCore
import Foundation

/// Native audio module for microphone recording (STT).
/// TTS playback is handled by @mykin-ai/expo-audio-stream.
public class AudioModule: Module {
    // Recording
    private var recordingEngine: AVAudioEngine?
    private var inputNode: AVAudioInputNode?
    private var isRecordingActive = false
    private var isMuted = false

    // Audio format: 16-bit PCM, 48kHz, mono
    private static let sampleRate: Double = 48000
    private static let recordingFormat = AVAudioFormat(
        commonFormat: .pcmFormatInt16,
        sampleRate: sampleRate,
        channels: 1,
        interleaved: false
    )!

    public func definition() -> ModuleDefinition {
        Name("Audio")

        Constants([
            "sampleRate": Self.sampleRate,
            "isLinear16PCM": true
        ])

        Events("onAudioInput", "onError")

        AsyncFunction("getPermissions") {
            return try await self.getPermissions()
        }

        AsyncFunction("startRecording") {
            let hasPermission = try await self.getPermissions()
            guard hasPermission else {
                throw NSError(
                    domain: "AudioModule",
                    code: 2,
                    userInfo: [NSLocalizedDescriptionKey: "Microphone permission not granted"]
                )
            }
            try self.startRecording()
        }

        AsyncFunction("stopRecording") {
            self.stopRecording()
        }

        AsyncFunction("mute") {
            self.isMuted = true
        }

        AsyncFunction("unmute") {
            self.isMuted = false
        }

        AsyncFunction("showMicrophoneModes") {
            if #available(iOS 15.0, *) {
                AVCaptureDevice.showSystemUserInterface(.microphoneModes)
            } else {
                throw NSError(
                    domain: "AudioModule",
                    code: 3,
                    userInfo: [NSLocalizedDescriptionKey: "Microphone modes are only available on iOS 15+"]
                )
            }
        }

        AsyncFunction("getMicrophoneMode") { () -> String in
            if #available(iOS 15.0, *) {
                let mode = AVCaptureDevice.preferredMicrophoneMode
                switch mode {
                case .standard:
                    return "Standard"
                case .voiceIsolation:
                    return "Voice Isolation"
                case .wideSpectrum:
                    return "Wide Spectrum"
                default:
                    throw NSError(
                        domain: "AudioModule",
                        code: 4,
                        userInfo: [NSLocalizedDescriptionKey: "Unknown microphone mode encountered"]
                    )
                }
            } else {
                return "N/A"
            }
        }
    }

    private func getPermissions() async throws -> Bool {
        let audioSession = AVAudioSession.sharedInstance()
        switch audioSession.recordPermission {
        case .granted:
            return true
        case .denied:
            return false
        case .undetermined:
            return await withCheckedContinuation { continuation in
                audioSession.requestRecordPermission { granted in
                    continuation.resume(returning: granted)
                }
            }
        @unknown default:
            throw NSError(
                domain: "AudioModule",
                code: 1,
                userInfo: [NSLocalizedDescriptionKey: "Unknown permission state"]
            )
        }
    }

    private func startRecording() throws {
        guard !isRecordingActive else { return }

        let audioSession = AVAudioSession.sharedInstance()
        try audioSession.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker, .allowBluetooth])
        try audioSession.setActive(true)

        recordingEngine = AVAudioEngine()
        guard let recordingEngine = recordingEngine else { return }

        inputNode = recordingEngine.inputNode
        guard let inputNode = inputNode else { return }

        let inputFormat = inputNode.outputFormat(forBus: 0)

        // Install tap on input node to capture audio
        inputNode.installTap(onBus: 0, bufferSize: 4096, format: inputFormat) { [weak self] buffer, _ in
            guard let self = self, !self.isMuted else { return }

            // Convert to 16-bit PCM
            guard let convertedBuffer = self.convertToInt16PCM(buffer: buffer) else { return }

            // Convert to base64
            let base64Audio = self.bufferToBase64(convertedBuffer)
            self.sendEvent("onAudioInput", ["base64EncodedAudio": base64Audio])
        }

        try recordingEngine.start()
        isRecordingActive = true
        print("[AudioModule] Recording started")
    }

    private func stopRecording() {
        guard isRecordingActive else { return }

        inputNode?.removeTap(onBus: 0)
        recordingEngine?.stop()
        recordingEngine = nil
        inputNode = nil
        isRecordingActive = false

        print("[AudioModule] Recording stopped")
    }

    private func convertToInt16PCM(buffer: AVAudioPCMBuffer) -> AVAudioPCMBuffer? {
        guard let converter = AVAudioConverter(from: buffer.format, to: Self.recordingFormat) else {
            return nil
        }

        let ratio = Self.sampleRate / buffer.format.sampleRate
        let outputFrameCapacity = AVAudioFrameCount(Double(buffer.frameLength) * ratio)

        guard let outputBuffer = AVAudioPCMBuffer(pcmFormat: Self.recordingFormat, frameCapacity: outputFrameCapacity) else {
            return nil
        }

        var error: NSError?
        converter.convert(to: outputBuffer, error: &error) { _, outStatus in
            outStatus.pointee = .haveData
            return buffer
        }

        if let error = error {
            print("[AudioModule] Conversion error: \(error)")
            return nil
        }

        return outputBuffer
    }

    private func bufferToBase64(_ buffer: AVAudioPCMBuffer) -> String {
        let channelData = buffer.int16ChannelData![0]
        let dataSize = Int(buffer.frameLength) * MemoryLayout<Int16>.size
        let data = Data(bytes: channelData, count: dataSize)
        return data.base64EncodedString()
    }
}
