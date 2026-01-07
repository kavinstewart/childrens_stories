import AVFoundation
import ExpoModulesCore
import Foundation
import Hume
import ObjCExceptionCatcher

public class AudioModule: Module {
    private let audioHub = AudioHub.shared
    private var audioHubIsPrepared = false
    private var isRecordingActive = false
    private var _soundPlayer: SoundPlayer?

    private static let audioFormat = AVAudioFormat(
        commonFormat: .pcmFormatInt16,
        sampleRate: 48000,
        channels: 1,
        interleaved: false
    )!

    private func handleMicrophoneData(_ data: Data, _: Float) {
        self.sendEvent("onAudioInput", ["base64EncodedAudio": data.base64EncodedString()])
    }

    private func handleAudioOutput(_ audioOutput: AudioOutput) {
        guard let clip = SoundClip.from(audioOutput) else {
            self.sendEvent("onError", ["message": "Failed to decode audio output"])
            return
        }
        playAudioClip(clip)
    }

    private func playAudioClip(_ clip: SoundClip) {
        Task {
            do {
                let soundPlayer = try await getSoundPlayer(format: Self.audioFormat)
                await soundPlayer.enqueueAudio(soundClip: clip)
            } catch {
                self.sendEvent("onError", ["message": error.localizedDescription])
            }
        }
    }

    private func getSoundPlayer(format: AVAudioFormat) async throws -> SoundPlayer {
        if let _soundPlayer {
            return _soundPlayer
        } else {
            _soundPlayer = SoundPlayer(format: format)
        }
        try await audioHub.addNode(_soundPlayer!.audioSourceNode, format: format)
        return _soundPlayer!
    }

    public func definition() -> ModuleDefinition {
        Name("Audio")

        Constants(["sampleRate": 48000, "isLinear16PCM": true])

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
            try await prepare()
            try await self.audioHub.startMicrophone(handler: handleMicrophoneData)
            self.isRecordingActive = true
        }

        AsyncFunction("stopRecording") {
            // Primary defense: only stop if we actually started recording
            guard self.isRecordingActive else {
                print("[AudioModule] stopRecording called but recording not active - skipping")
                return
            }

            // Reset state immediately to prevent double-stop
            self.isRecordingActive = false

            // Secondary defense: catch ObjC exceptions from Hume SDK
            // The SDK's stopMicrophone() can throw NSException when AVAudioEngine is in invalid state
            var error: NSError?
            let success = ObjCExceptionCatcher.tryBlock({
                // Use a semaphore to bridge async to sync for the ObjC block
                let semaphore = DispatchSemaphore(value: 0)
                Task {
                    await self.audioHub.stopMicrophone()
                    semaphore.signal()
                }
                semaphore.wait()
            }, error: &error)

            if !success {
                print("[AudioModule] stopMicrophone threw exception: \(error?.localizedDescription ?? "unknown")")
                // Fallback: force release audio session to clean up resources
                do {
                    try AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
                } catch {
                    print("[AudioModule] Failed to deactivate audio session: \(error)")
                }
            }
        }

        AsyncFunction("mute") {
            await audioHub.muteMic(true)
        }

        AsyncFunction("unmute") {
            await audioHub.muteMic(false)
        }

        AsyncFunction("enqueueAudio") { (base64EncodedAudio: String) in
            try await prepare()
            guard let audioData = Data(base64Encoded: base64EncodedAudio) else {
                self.sendEvent("onError", ["message": "Invalid base64 audio data"])
                return
            }
            guard let clip = SoundClip.from(audioData) else {
                self.sendEvent("onError", ["message": "Failed to create sound clip"])
                return
            }
            self.playAudioClip(clip)
        }

        AsyncFunction("stopPlayback") {
            await _soundPlayer?.clearQueue()
        }

        AsyncFunction("showMicrophoneModes") {
            if #available(iOS 15.0, *) {
                let wasRecording = await self.audioHub.isRecording

                if !wasRecording {
                    try await self.prepare()
                    try await self.audioHub.startMicrophone(handler: { _, _ in })
                }

                AVCaptureDevice.showSystemUserInterface(.microphoneModes)

                if !wasRecording {
                    await self.audioHub.stopMicrophone()
                }
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

    private func prepare() async throws {
        guard !audioHubIsPrepared else { return }
        await self.audioHub.prepare()
        audioHubIsPrepared = true
    }
}
