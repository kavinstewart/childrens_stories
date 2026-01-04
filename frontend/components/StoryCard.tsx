import { View, Text, Pressable, Image } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { api, Story, StoryRecommendation } from '@/lib/api';

// Color gradients for story cards based on index or id
const cardColors: readonly [string, string][] = [
  ['#FCD34D', '#F97316'], // amber/orange
  ['#A78BFA', '#7C3AED'], // purple
  ['#F472B6', '#EC4899'], // pink
  ['#22D3EE', '#3B82F6'], // cyan/blue
  ['#34D399', '#10B981'], // green
  ['#FB923C', '#EA580C'], // orange
];

// Icons based on theme or goal keywords
function getStoryIcon(goal: string, title?: string): string {
  const text = ((goal || '') + ' ' + (title || '')).toLowerCase();

  if (text.includes('bear')) return '🐻';
  if (text.includes('space') || text.includes('rocket')) return '🚀';
  if (text.includes('ocean') || text.includes('fish') || text.includes('sea')) return '🐠';
  if (text.includes('garden') || text.includes('flower')) return '🌻';
  if (text.includes('friend')) return '👫';
  if (text.includes('brave') || text.includes('courage')) return '🦸';
  if (text.includes('kind')) return '💝';
  if (text.includes('share') || text.includes('sharing')) return '🤝';
  if (text.includes('color')) return '🌈';
  if (text.includes('count')) return '🔢';
  if (text.includes('mouse') || text.includes('mice')) return '🐭';
  if (text.includes('cat')) return '🐱';
  if (text.includes('dog')) return '🐶';
  if (text.includes('bird')) return '🐦';
  if (text.includes('magic') || text.includes('wizard')) return '🧙‍♂️';
  return '📖'; // default book icon
}

interface StoryCardProps {
  // Accept either a full Story or a StoryRecommendation
  story?: Story;
  recommendation?: StoryRecommendation;
  width: number;
  height: number;
  colorIndex?: number;
  onPress: () => void;
  showStatusBadge?: boolean;
}

export function StoryCard({
  story,
  recommendation,
  width,
  height,
  colorIndex = 0,
  onPress,
  showStatusBadge = false,
}: StoryCardProps) {
  // Normalize data from either story or recommendation
  const id = story?.id || recommendation?.id || '';
  const title = story?.title || recommendation?.title;
  const goal = story?.goal || recommendation?.goal || '';
  const isIllustrated = story?.is_illustrated ?? recommendation?.is_illustrated ?? false;
  const status = story?.status;

  // Get cover image URL
  const coverUrl = isIllustrated ? api.getSpreadImageUrl(id, 1) : null;

  // Calculate section heights (70% illustration, 30% info - matches library)
  const illustrationHeight = height * 0.70;
  const infoHeight = height * 0.30;

  // Get gradient colors based on index or id
  const gradientIndex = colorIndex || (id.charCodeAt(0) % cardColors.length);
  const gradientColors = cardColors[gradientIndex];

  // Get icon for non-illustrated stories
  const icon = getStoryIcon(goal, title);

  return (
    <View style={{ width, height }}>
      <Pressable
        onPress={onPress}
        style={({ pressed }) => ({
          flex: 1,
          borderRadius: 16,
          overflow: 'hidden',
          opacity: pressed ? 0.9 : 1,
          transform: [{ scale: pressed ? 0.98 : 1 }],
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 2 },
          shadowOpacity: 0.1,
          shadowRadius: 4,
          elevation: 3,
        })}
      >
        {/* Illustration area - 70% height */}
        <View style={{
          height: illustrationHeight,
          borderTopLeftRadius: 16,
          borderTopRightRadius: 16,
          overflow: 'hidden',
        }}>
          {coverUrl ? (
            <Image
              source={{ uri: coverUrl }}
              style={{ width: '100%', height: '100%' }}
              resizeMode="cover"
              onError={(e) => console.error(`[Image] StoryCard failed to load: ${coverUrl}`, e.nativeEvent.error)}
              onLoad={() => console.log(`[Image] StoryCard loaded: ${coverUrl}`)}
            />
          ) : (
            <LinearGradient
              colors={gradientColors}
              style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}
            >
              <Text style={{ fontSize: 48 }}>{icon}</Text>
            </LinearGradient>
          )}

          {/* Status badge (optional, for library view) */}
          {showStatusBadge && status && (
            <>
              {(status === 'pending' || status === 'running') && (
                <View style={{ position: 'absolute', top: 8, right: 8, backgroundColor: 'rgba(255,255,255,0.9)', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12 }}>
                  <Text style={{ fontSize: 12 }}>⏳</Text>
                </View>
              )}
              {status === 'failed' && (
                <View style={{ position: 'absolute', top: 8, right: 8, backgroundColor: '#EF4444', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12 }}>
                  <Text style={{ fontSize: 12 }}>❌</Text>
                </View>
              )}
              {status === 'completed' && (
                <View style={{ position: 'absolute', top: 8, right: 8, backgroundColor: 'rgba(34,197,94,0.9)', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12 }}>
                  <Text style={{ fontSize: 12, color: 'white' }}>✓</Text>
                </View>
              )}
            </>
          )}
        </View>

        {/* Info section - 30% height, title only */}
        <View style={{
          height: infoHeight,
          backgroundColor: '#FEF3C7',
          paddingHorizontal: 12,
          paddingVertical: 10,
          justifyContent: 'center',
          borderBottomLeftRadius: 16,
          borderBottomRightRadius: 16,
        }}>
          <Text
            style={{ color: '#1F2937', fontWeight: 'bold', fontSize: 18, lineHeight: 22 }}
            numberOfLines={2}
          >
            {title || goal || 'Untitled Story'}
          </Text>
        </View>
      </Pressable>
    </View>
  );
}
