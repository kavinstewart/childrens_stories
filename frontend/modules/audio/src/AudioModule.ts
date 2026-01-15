import { NativeModule, requireNativeModule } from 'expo';
import { AudioModuleEvents, MicrophoneMode } from './AudioModule.types';

declare class AudioModule extends NativeModule<AudioModuleEvents> {
  getPermissions(): Promise<boolean>;
  startRecording(): Promise<void>;
  stopRecording(): Promise<void>;
  mute(): Promise<void>;
  unmute(): Promise<void>;
  showMicrophoneModes(): Promise<void>;
  getMicrophoneMode(): Promise<MicrophoneMode>;
}

export default requireNativeModule<AudioModule>('Audio');
