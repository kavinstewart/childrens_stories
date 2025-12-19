import { View, Text, Pressable } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { useEffect, useState } from 'react';
import { useStoryPolling } from '@/features/stories/hooks';
import { fontFamily } from '@/lib/fonts';
import {
  FloatingElement,
  BobbingCharacter,
  MagicParticles,
  Firefly,
  StageIcon,
  CompletePop,
} from '@/components/animations';

// Whimsical creation stages that cycle through during generation
const creationStages = [
  { message: 'Opening the story vault', icon: '\u{1F4D6}' },
  { message: 'Gathering magical ingredients', icon: '\u2728' },
  { message: 'Waking up the characters', icon: '\u{1F31F}' },
  { message: 'Sprinkling in some adventure', icon: '\u{1F5FA}\uFE0F' },
  { message: 'Mixing in a pinch of wonder', icon: '\u{1F52E}' },
  { message: 'Painting the scenes', icon: '\u{1F3A8}' },
  { message: 'Adding a twist', icon: '\u{1F300}' },
  { message: 'Polishing the ending', icon: '\u{1F48E}' },
  { message: 'Your story is ready!', icon: '\u{1F389}' },
];

// Status mapping to handle API status transitions
const statusStages = {
  pending: { label: 'Getting ready...', icon: '\u{1F31F}' },
  running: null, // Will use cycling stages
  completed: { label: 'Your story is ready!', icon: '\u{1F389}' },
  failed: { label: 'Oops, something went wrong', icon: '\u{1F622}' },
};

export default function CreatingStory() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: story, error } = useStoryPolling(id);

  // Animated stage progression while running
  const [currentStageIndex, setCurrentStageIndex] = useState(0);
  const [completedStages, setCompletedStages] = useState<number[]>([]);
  const [showReadButton, setShowReadButton] = useState(false);

  // Cycle through stages while story is being generated
  useEffect(() => {
    if (story?.status !== 'running') return;

    // Don't go to the last stage (that's for completion)
    const maxStage = creationStages.length - 2;

    const interval = setInterval(() => {
      setCurrentStageIndex((prev) => {
        const next = prev < maxStage ? prev + 1 : 0;
        // Track completed stages (but cycle back)
        if (next > 0) {
          setCompletedStages((cs) => {
            if (!cs.includes(prev) && cs.length < 7) {
              return [...cs, prev];
            }
            return cs;
          });
        }
        return next;
      });
    }, 2500);

    return () => clearInterval(interval);
  }, [story?.status]);

  // Show completion state and then the Read button
  useEffect(() => {
    if (story?.status === 'completed') {
      setCurrentStageIndex(creationStages.length - 1);
      // Show Read button after a moment
      const timer = setTimeout(() => {
        setShowReadButton(true);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [story?.status]);

  // Get current display info
  const isRunning = story?.status === 'running';
  const isCompleted = story?.status === 'completed';
  const isFailed = story?.status === 'failed';

  const currentStage =
    isRunning || isCompleted
      ? creationStages[currentStageIndex]
      : statusStages[story?.status ?? 'pending'] || statusStages.pending;

  // Calculate progress - use API progress when available, otherwise estimate
  const progress = isCompleted
    ? 100
    : isFailed
      ? 100
      : story?.progress?.percentage ?? (isRunning ? Math.min(10 + currentStageIndex * 11, 90) : 5);

  // Use API stage detail when available for more accurate status
  const apiStageDetail = story?.progress?.stage_detail;

  const handleReadStory = () => {
    router.replace(`/read/${id}`);
  };

  const handleCancel = () => {
    router.replace('/');
  };

  return (
    <LinearGradient
      colors={
        isFailed
          ? ['#FCA5A5', '#EF4444', '#DC2626']
          : ['#C4B5FD', '#A78BFA', '#8B5CF6']
      }
      style={{ flex: 1 }}
    >
      {/* Floating decorations */}
      <FloatingElement delay={1.5} duration={5} style={{ top: 96, right: 48 }}>
        <Text style={{ fontSize: 20, opacity: 0.3 }}>{'\u2B50'}</Text>
      </FloatingElement>
      <FloatingElement delay={0.5} duration={4.5} style={{ bottom: 128, left: 48 }}>
        <Text style={{ fontSize: 24, opacity: 0.35 }}>{'\u{1F319}'}</Text>
      </FloatingElement>
      <FloatingElement delay={2} duration={5} style={{ bottom: 96, right: 32 }}>
        <Text style={{ fontSize: 20, opacity: 0.3 }}>{'\u2728'}</Text>
      </FloatingElement>

      {/* Fireflies */}
      <Firefly delay={0} x="20%" y="30%" />
      <Firefly delay={0.8} x="70%" y="25%" />
      <Firefly delay={1.5} x="15%" y="60%" />
      <Firefly delay={2.2} x="80%" y="55%" />
      <Firefly delay={0.5} x="50%" y="70%" />

      {/* Main content */}
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        {/* User's prompt echo */}
        {story?.goal && (
          <View
            style={{
              backgroundColor: 'rgba(255,255,255,0.4)',
              borderRadius: 16,
              padding: 12,
              marginBottom: 48,
              maxWidth: 400,
            }}
          >
            <Text
              style={{
                fontFamily: fontFamily.nunito,
                fontSize: 12,
                color: '#6B7280',
                textAlign: 'center',
                marginBottom: 2,
              }}
            >
              Creating a story about...
            </Text>
            <Text
              style={{
                fontFamily: fontFamily.nunitoSemiBold,
                fontSize: 16,
                color: '#374151',
                textAlign: 'center',
              }}
            >
              "{story.goal}"
            </Text>
          </View>
        )}

        {/* Bobbing character with magic particles */}
        <View style={{ position: 'relative', marginBottom: 40 }}>
          <BobbingCharacter
            cycling={isRunning}
            size={120}
          />
          {!isFailed && <MagicParticles />}
        </View>

        {/* Current stage message */}
        <View
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            gap: 12,
            marginBottom: 12,
          }}
        >
          <StageIcon
            emoji={currentStage?.icon ?? '\u{1F31F}'}
            size={36}
            stageKey={currentStageIndex}
          />
          <Text
            style={{
              fontFamily: fontFamily.nunitoBold,
              fontSize: 22,
              color: 'white',
            }}
          >
            {'message' in currentStage ? currentStage.message : currentStage.label}
            {isRunning && !isCompleted && (
              <Text style={{ opacity: 0.6 }}>...</Text>
            )}
          </Text>
        </View>

        {/* Real-time API stage detail */}
        {apiStageDetail && isRunning && (
          <Text
            style={{
              fontFamily: fontFamily.nunito,
              fontSize: 14,
              color: 'rgba(255,255,255,0.7)',
              marginBottom: 20,
            }}
          >
            {apiStageDetail}
          </Text>
        )}

        {/* Progress bar */}
        <View
          style={{
            width: 320,
            height: 12,
            backgroundColor: 'rgba(255,255,255,0.3)',
            borderRadius: 6,
            overflow: 'hidden',
            marginBottom: 8,
          }}
        >
          <LinearGradient
            colors={['#A855F7', '#EC4899', '#F59E0B']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={{
              height: '100%',
              width: `${progress}%`,
              borderRadius: 6,
            }}
          />
        </View>

        {/* Progress counters from API */}
        {isRunning && (story?.progress?.spreads_total || story?.progress?.characters_total) && (
          <Text
            style={{
              fontFamily: fontFamily.nunito,
              fontSize: 12,
              color: 'rgba(255,255,255,0.6)',
              marginBottom: 12,
            }}
          >
            {story?.progress?.characters_total && story.progress.stage === 'character_refs'
              ? `Characters: ${story.progress.characters_completed ?? 0}/${story.progress.characters_total}`
              : story?.progress?.spreads_total
                ? `Illustrations: ${story.progress.spreads_completed ?? 0}/${story.progress.spreads_total}`
                : null}
          </Text>
        )}

        {/* Stage history icons */}
        <View
          style={{
            flexDirection: 'row',
            gap: 8,
            height: 40,
            alignItems: 'center',
          }}
        >
          {completedStages.slice(-7).map((stageIdx) => (
            <View
              key={stageIdx}
              style={{
                width: 36,
                height: 36,
                backgroundColor: 'rgba(255,255,255,0.7)',
                borderRadius: 18,
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Text style={{ fontSize: 16 }}>{creationStages[stageIdx].icon}</Text>
            </View>
          ))}
        </View>

        {/* Story info when available */}
        {story?.title && isRunning && (
          <Text
            style={{
              fontFamily: fontFamily.nunito,
              fontSize: 16,
              color: 'rgba(255,255,255,0.8)',
              marginTop: 16,
              textAlign: 'center',
            }}
          >
            "{story.title}"
          </Text>
        )}

        {/* Completion state - Read Your Story button */}
        {isCompleted && showReadButton && (
          <CompletePop style={{ marginTop: 40 }}>
            <Pressable
              onPress={handleReadStory}
              style={({ pressed }) => ({
                opacity: pressed ? 0.9 : 1,
                transform: [{ scale: pressed ? 0.98 : 1 }],
              })}
            >
              <LinearGradient
                colors={['#EC4899', '#8B5CF6', '#6366F1']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: 12,
                  paddingVertical: 16,
                  paddingHorizontal: 32,
                  borderRadius: 16,
                  shadowColor: '#000',
                  shadowOffset: { width: 0, height: 4 },
                  shadowOpacity: 0.3,
                  shadowRadius: 8,
                  elevation: 8,
                }}
              >
                <Text style={{ fontSize: 24 }}>{'\u{1F4D6}'}</Text>
                <Text
                  style={{
                    fontFamily: fontFamily.nunitoBold,
                    fontSize: 18,
                    color: 'white',
                  }}
                >
                  Read Your Story!
                </Text>
                <Text style={{ fontSize: 24 }}>{'\u2728'}</Text>
              </LinearGradient>
            </Pressable>
          </CompletePop>
        )}

        {/* Failed state buttons */}
        {isFailed && (
          <View style={{ marginTop: 32 }}>
            {story?.error_message && (
              <Text
                style={{
                  fontFamily: fontFamily.nunito,
                  fontSize: 16,
                  color: 'rgba(255,255,255,0.8)',
                  textAlign: 'center',
                  marginBottom: 24,
                  paddingHorizontal: 32,
                }}
              >
                {story.error_message}
              </Text>
            )}
            <View style={{ flexDirection: 'row', gap: 16 }}>
              <Pressable
                onPress={() => router.replace('/')}
                style={{
                  backgroundColor: 'rgba(255,255,255,0.2)',
                  paddingHorizontal: 24,
                  paddingVertical: 12,
                  borderRadius: 12,
                }}
              >
                <Text
                  style={{
                    fontFamily: fontFamily.nunitoBold,
                    color: 'white',
                  }}
                >
                  Go Home
                </Text>
              </Pressable>
              <Pressable
                onPress={() => router.replace('/new')}
                style={{
                  backgroundColor: 'white',
                  paddingHorizontal: 24,
                  paddingVertical: 12,
                  borderRadius: 12,
                }}
              >
                <Text
                  style={{
                    fontFamily: fontFamily.nunitoBold,
                    color: '#7C3AED',
                  }}
                >
                  Try Again
                </Text>
              </Pressable>
            </View>
          </View>
        )}

        {/* API error state */}
        {error && (
          <View style={{ marginTop: 32, alignItems: 'center' }}>
            <Text
              style={{
                fontFamily: fontFamily.nunito,
                color: 'rgba(255,255,255,0.8)',
                marginBottom: 16,
              }}
            >
              Couldn't connect to server
            </Text>
            <Pressable
              onPress={() => router.replace('/')}
              style={{
                backgroundColor: 'white',
                paddingHorizontal: 24,
                paddingVertical: 12,
                borderRadius: 12,
              }}
            >
              <Text
                style={{
                  fontFamily: fontFamily.nunitoBold,
                  color: '#7C3AED',
                }}
              >
                Go Home
              </Text>
            </Pressable>
          </View>
        )}

        {/* Cancel button (only while in progress) */}
        {!isCompleted && !isFailed && !error && (
          <Pressable
            onPress={handleCancel}
            style={{ marginTop: 40 }}
          >
            <Text
              style={{
                fontFamily: fontFamily.nunitoSemiBold,
                fontSize: 14,
                color: 'rgba(255,255,255,0.6)',
              }}
            >
              Cancel
            </Text>
          </Pressable>
        )}
      </View>
    </LinearGradient>
  );
}
