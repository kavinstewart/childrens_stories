import AVFoundation
import ExpoModulesCore
import Foundation

public class AudioModule: Module {
    private var audioEngine: AVAudioEngine?
    private var inputNode: AVAudioInputNode?
    private var isRecordingActive = false
    private var isMuted = false

    // Audio playback
    private var audioPlayer: AVAudioPlayerNode?
    private var playbackQueue: [Data] = []
    private var isPlaying = false

    // Audio format: 16-bit PCM, 48kHz, mono
    private static let sampleRate: Double = 48000
    private static let recordingFormat = AVAudioFormat(
        commonFormat: .pcmFormatInt16,
        sampleRate: sampleRate,
        channels: 1,
        interleaved: false
    )!

    private static let playbackFormat = AVAudioFormat(
        commonFormat: .pcmFormatInt16,
        sampleRate: 24000,
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

        AsyncFunction("enqueueAudio") { (base64EncodedAudio: String) in
            guard let audioData = Data(base64Encoded: base64EncodedAudio) else {
                self.sendEvent("onError", ["message": "Invalid base64 audio data"])
                return
            }
            self.playbackQueue.append(audioData)
            self.playNextInQueue()
        }

        AsyncFunction("stopPlayback") {
            self.stopPlayback()
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

        audioEngine = AVAudioEngine()
        guard let audioEngine = audioEngine else { return }

        inputNode = audioEngine.inputNode
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

        try audioEngine.start()
        isRecordingActive = true
        print("[AudioModule] Recording started")
    }

    private func stopRecording() {
        guard isRecordingActive else { return }

        inputNode?.removeTap(onBus: 0)
        audioEngine?.stop()
        audioEngine = nil
        inputNode = nil
        isRecordingActive = false

        do {
            try AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        } catch {
            print("[AudioModule] Failed to deactivate audio session: \(error)")
        }

        print("[AudioModule] Recording stopped")
    }

    private func playNextInQueue() {
        guard !isPlaying, !playbackQueue.isEmpty else { return }
        isPlaying = true

        let audioData = playbackQueue.removeFirst()

        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.playback, mode: .default)
            try audioSession.setActive(true)

            // Create audio player if needed
            if audioPlayer == nil {
                audioPlayer = AVAudioPlayerNode()
                audioEngine = AVAudioEngine()
                audioEngine?.attach(audioPlayer!)
                audioEngine?.connect(audioPlayer!, to: audioEngine!.mainMixerNode, format: Self.playbackFormat)
            }

            guard let audioEngine = audioEngine, let audioPlayer = audioPlayer else {
                isPlaying = false
                return
            }

            // Convert data to audio buffer
            let frameCount = UInt32(audioData.count / 2) // 16-bit = 2 bytes per sample
            guard let buffer = AVAudioPCMBuffer(pcmFormat: Self.playbackFormat, frameCapacity: frameCount) else {
                isPlaying = false
                return
            }
            buffer.frameLength = frameCount

            // Copy data to buffer
            audioData.withUnsafeBytes { rawPtr in
                guard let baseAddress = rawPtr.baseAddress else { return }
                memcpy(buffer.int16ChannelData![0], baseAddress, audioData.count)
            }

            if !audioEngine.isRunning {
                try audioEngine.start()
            }

            audioPlayer.scheduleBuffer(buffer) { [weak self] in
                DispatchQueue.main.async {
                    self?.isPlaying = false
                    self?.playNextInQueue()
                }
            }

            if !audioPlayer.isPlaying {
                audioPlayer.play()
            }
        } catch {
            print("[AudioModule] Playback error: \(error)")
            sendEvent("onError", ["message": error.localizedDescription])
            isPlaying = false
        }
    }

    private func stopPlayback() {
        audioPlayer?.stop()
        playbackQueue.removeAll()
        isPlaying = false
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
