import { EventEmitter } from 'expo-modules-core';
import { AudioModuleEvents, MicrophoneMode } from './AudioModule.types';

const emitter = new EventEmitter<AudioModuleEvents>();

let audioContext: AudioContext | null = null;
let mediaStream: MediaStream | null = null;
let processor: ScriptProcessorNode | null = null;
let source: MediaStreamAudioSourceNode | null = null;
let isMuted = false;

// Convert Float32 PCM to base64-encoded Int16 PCM
function float32ToBase64Int16(float32Array: Float32Array): string {
  const int16Array = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  const uint8Array = new Uint8Array(int16Array.buffer);
  let binary = '';
  for (let i = 0; i < uint8Array.length; i++) {
    binary += String.fromCharCode(uint8Array[i]);
  }
  return btoa(binary);
}

export default {
  sampleRate: 48000,
  isLinear16PCM: true,

  async getPermissions(): Promise<boolean> {
    console.log('[AudioModule.web] Requesting microphone permissions...');
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('[AudioModule.web] Microphone permissions granted.');
      return true;
    } catch {
      console.log('[AudioModule.web] Microphone permissions denied.');
      return false;
    }
  },

  async startRecording(): Promise<void> {
    console.log('[AudioModule.web] Starting audio recording...');

    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 48000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    audioContext = new AudioContext({ sampleRate: 48000 });
    source = audioContext.createMediaStreamSource(mediaStream);

    // Use ScriptProcessorNode for capturing raw PCM
    // Note: ScriptProcessorNode is deprecated but widely supported
    // AudioWorklet would be the modern replacement
    processor = audioContext.createScriptProcessor(4096, 1, 1);

    processor.onaudioprocess = (event) => {
      if (isMuted) return;
      const inputData = event.inputBuffer.getChannelData(0);
      const base64EncodedAudio = float32ToBase64Int16(inputData);
      emitter.emit('onAudioInput', { base64EncodedAudio });
    };

    source.connect(processor);
    processor.connect(audioContext.destination);

    console.log('[AudioModule.web] Audio recording started.');
  },

  async stopRecording(): Promise<void> {
    console.log('[AudioModule.web] Stopping audio recording...');

    if (processor) {
      processor.disconnect();
      processor = null;
    }
    if (source) {
      source.disconnect();
      source = null;
    }
    if (audioContext) {
      await audioContext.close();
      audioContext = null;
    }
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
      mediaStream = null;
    }

    console.log('[AudioModule.web] Audio recording stopped.');
  },

  async mute(): Promise<void> {
    isMuted = true;
  },

  async unmute(): Promise<void> {
    isMuted = false;
  },

  addListener(
    eventName: keyof AudioModuleEvents,
    f: AudioModuleEvents[typeof eventName]
  ): { remove: () => void } {
    return emitter.addListener(eventName, f);
  },

  async showMicrophoneModes(): Promise<void> {
    console.log('[AudioModule.web] Microphone modes are only available on iOS');
    return;
  },

  async getMicrophoneMode(): Promise<MicrophoneMode> {
    return 'N/A';
  },
};
