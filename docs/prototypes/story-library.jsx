import { useState } from 'react';

const stories = [
  {
    id: 1,
    title: "The Bear Who Shared",
    theme: "sharing",
    pages: 32,
    date: "Dec 17",
    progress: 100,
    color: "from-amber-400 to-orange-500",
    bgColor: "bg-amber-50",
    icon: "🐻",
    accent: "#f59e0b"
  },
  {
    id: 2,
    title: "Space Rocket Zoom",
    theme: "counting",
    pages: 12,
    date: "Dec 15",
    progress: 45,
    color: "from-violet-500 to-purple-600",
    bgColor: "bg-violet-50",
    icon: "🚀",
    accent: "#8b5cf6"
  },
  {
    id: 3,
    title: "Luna's Lost Mitten",
    theme: "kindness",
    pages: 24,
    date: "Dec 10",
    progress: 0,
    color: "from-pink-400 to-rose-500",
    bgColor: "bg-pink-50",
    icon: "🧤",
    accent: "#ec4899"
  },
  {
    id: 4,
    title: "Colors of the Ocean",
    theme: "colors",
    pages: 18,
    date: "Dec 08",
    progress: 100,
    color: "from-cyan-400 to-blue-500",
    bgColor: "bg-cyan-50",
    icon: "🐠",
    accent: "#06b6d4"
  },
  {
    id: 5,
    title: "Max and the Big Storm",
    theme: "bravery",
    pages: 28,
    date: "Nov 22",
    progress: 72,
    color: "from-emerald-400 to-teal-500",
    bgColor: "bg-emerald-50",
    icon: "⛈️",
    accent: "#10b981"
  },
  {
    id: 6,
    title: "The Giggling Garden",
    theme: "friendship",
    pages: 20,
    date: "Nov 15",
    progress: 0,
    color: "from-lime-400 to-green-500",
    bgColor: "bg-lime-50",
    icon: "🌻",
    accent: "#84cc16"
  },
  {
    id: 7,
    title: "Penny's Paper Plane",
    theme: "creativity",
    pages: 16,
    date: "Nov 10",
    progress: 100,
    color: "from-sky-400 to-blue-500",
    bgColor: "bg-sky-50",
    icon: "✈️",
    accent: "#0ea5e9"
  },
  {
    id: 8,
    title: "The Sleepy Sloth",
    theme: "patience",
    pages: 22,
    date: "Nov 05",
    progress: 30,
    color: "from-stone-400 to-stone-600",
    bgColor: "bg-stone-100",
    icon: "🦥",
    accent: "#78716c"
  }
];

const themeLabels = {
  sharing: "Sharing",
  counting: "Counting",
  kindness: "Kindness",
  colors: "Colors",
  bravery: "Bravery",
  friendship: "Friendship",
  creativity: "Creativity",
  patience: "Patience"
};

function StoryCard({ story, index }) {
  const [isHovered, setIsHovered] = useState(false);
  
  return (
    <div
      className="group relative cursor-pointer"
      style={{
        animation: `floatIn 0.6s ease-out ${index * 0.08}s both`
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Card - min-h-[44px] touch targets built into clickable area */}
      <div 
        className={`relative rounded-2xl lg:rounded-3xl overflow-hidden transition-all duration-500 ${
          isHovered ? 'scale-105 shadow-2xl' : 'shadow-lg'
        }`}
        style={{
          transform: isHovered ? 'translateY(-8px) rotate(1deg)' : 'translateY(0) rotate(0deg)'
        }}
      >
        {/* Book Cover - compact height */}
        <div className={`relative h-28 sm:h-32 md:h-36 lg:h-40 bg-gradient-to-br ${story.color} p-4 overflow-hidden`}>
          {/* Decorative circles */}
          <div className="absolute -top-6 -right-6 w-16 h-16 sm:w-20 sm:h-20 bg-white/10 rounded-full" />
          <div className="absolute -bottom-8 -left-8 w-24 h-24 sm:w-28 sm:h-28 bg-white/10 rounded-full" />
          <div className="absolute top-1/2 right-4 w-10 h-10 sm:w-12 sm:h-12 bg-white/5 rounded-full" />
          
          {/* Icon */}
          <div 
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-4xl sm:text-5xl md:text-5xl lg:text-6xl transition-transform duration-500"
            style={{
              transform: isHovered 
                ? 'translate(-50%, -50%) scale(1.2) rotate(-5deg)' 
                : 'translate(-50%, -50%) scale(1) rotate(0deg)',
              filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.2))'
            }}
          >
            {story.icon}
          </div>
          
          {/* Progress badge - touch-friendly size */}
          {story.progress === 100 && (
            <div className="absolute top-2 right-2 bg-white/90 backdrop-blur-sm rounded-full px-2 py-0.5 sm:px-2.5 sm:py-1 flex items-center gap-1 shadow-md min-h-[26px]">
              <span className="text-green-500 text-xs sm:text-sm">✓</span>
              <span className="text-[10px] sm:text-xs font-semibold text-gray-700">Done</span>
            </div>
          )}
          {story.progress > 0 && story.progress < 100 && (
            <div className="absolute top-2 right-2 bg-white/90 backdrop-blur-sm rounded-full px-2 py-0.5 sm:px-2.5 sm:py-1 shadow-md min-h-[26px] flex items-center">
              <span className="text-[10px] sm:text-xs font-semibold text-gray-700">{story.progress}%</span>
            </div>
          )}
        </div>
        
        {/* Info section */}
        <div className={`${story.bgColor} p-2.5 sm:p-3 lg:p-4`}>
          <h3 className="font-bold text-gray-800 text-sm sm:text-base lg:text-lg leading-tight mb-1.5 sm:mb-2 line-clamp-2" style={{ fontFamily: "'Nunito', sans-serif" }}>
            {story.title}
          </h3>
          
          <div className="flex items-center justify-between gap-2">
            <div 
              className="text-[10px] sm:text-xs font-semibold px-2 py-0.5 sm:py-1 rounded-full text-white min-h-[22px] sm:min-h-[26px] flex items-center"
              style={{ backgroundColor: story.accent }}
            >
              {themeLabels[story.theme]}
            </div>
            <span className="text-[10px] sm:text-xs text-gray-500 font-medium whitespace-nowrap">{story.pages} pg</span>
          </div>
          
          {/* Progress bar */}
          {story.progress > 0 && story.progress < 100 && (
            <div className="mt-2 sm:mt-2.5">
              <div className="h-1 sm:h-1.5 bg-gray-200 rounded-full overflow-hidden">
                <div 
                  className={`h-full bg-gradient-to-r ${story.color} rounded-full transition-all duration-700`}
                  style={{ width: `${story.progress}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FloatingElement({ children, delay, duration, className }) {
  return (
    <div 
      className={`absolute pointer-events-none select-none ${className}`}
      style={{
        animation: `float ${duration}s ease-in-out ${delay}s infinite`
      }}
    >
      {children}
    </div>
  );
}

export default function StoryLibrary() {
  const [filter, setFilter] = useState('all');
  
  const filteredStories = filter === 'all' 
    ? stories 
    : filter === 'unread' 
      ? stories.filter(s => s.progress === 0)
      : filter === 'reading'
        ? stories.filter(s => s.progress > 0 && s.progress < 100)
        : stories.filter(s => s.progress === 100);

  const finishedCount = stories.filter(s => s.progress === 100).length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-100 via-purple-50 to-pink-100 relative overflow-hidden">
      {/* CSS Animations */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&family=Baloo+2:wght@700;800&display=swap');
        
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-20px) rotate(5deg); }
        }
        
        @keyframes floatIn {
          from {
            opacity: 0;
            transform: translateY(30px) scale(0.9);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        
        @keyframes wiggle {
          0%, 100% { transform: rotate(-3deg); }
          50% { transform: rotate(3deg); }
        }
        
        .new-story-btn:hover, .new-story-btn:active {
          animation: wiggle 0.3s ease-in-out infinite;
        }
        
        .line-clamp-2 {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
        
        .scrollbar-hide {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
      `}</style>
      
      {/* Floating decorations - hidden on smaller tablets for performance */}
      <FloatingElement delay={0} duration={4} className="top-16 left-8 text-2xl sm:text-3xl opacity-40 hidden sm:block">⭐</FloatingElement>
      <FloatingElement delay={1} duration={5} className="top-24 right-12 text-xl sm:text-2xl opacity-30 hidden sm:block">🌙</FloatingElement>
      <FloatingElement delay={2} duration={4.5} className="bottom-24 left-12 text-xl sm:text-2xl opacity-30 hidden md:block">✨</FloatingElement>
      <FloatingElement delay={0.5} duration={5.5} className="bottom-16 right-8 text-2xl sm:text-3xl opacity-40 hidden sm:block">📚</FloatingElement>
      
      {/* Main content - max-w-7xl for larger iPads */}
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6 lg:py-8">
        {/* Header - horizontal layout */}
        <div className="flex items-center justify-between gap-4 mb-4 sm:mb-6 lg:mb-8">
          <div>
            <h1 
              className="text-2xl sm:text-3xl lg:text-4xl xl:text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-purple-600 via-pink-500 to-orange-400 mb-0.5 sm:mb-1"
              style={{ fontFamily: "'Baloo 2', cursive" }}
            >
              My Story Library
            </h1>
            <p className="text-gray-600 text-sm sm:text-base lg:text-lg" style={{ fontFamily: "'Nunito', sans-serif" }}>
              {stories.length} magical adventures waiting! ✨
            </p>
          </div>
          
          {/* New Story Button - fixed width, not flex-grow */}
          <button className="new-story-btn relative bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500 text-white font-bold py-3 px-5 sm:px-6 lg:py-4 lg:px-8 rounded-xl lg:rounded-2xl shadow-lg hover:shadow-xl active:scale-95 transition-all inline-flex items-center gap-2 min-h-[48px]">
            <span className="text-lg sm:text-xl lg:text-2xl">✨</span>
            <span style={{ fontFamily: "'Nunito', sans-serif" }} className="text-base lg:text-lg font-bold whitespace-nowrap">New Story</span>
            <div className="absolute -top-1 -right-1 w-3 h-3 bg-yellow-400 rounded-full animate-pulse" />
          </button>
        </div>
        
        {/* Filters - horizontal scroll on mobile, inline on tablet */}
        <div className="flex gap-2 mb-4 sm:mb-6 overflow-x-auto pb-2 scrollbar-hide" style={{ fontFamily: "'Nunito', sans-serif" }}>
          {[
            { key: 'all', label: 'All Stories', shortLabel: 'All', icon: '📚' },
            { key: 'unread', label: 'Not Started', shortLabel: 'New', icon: '🆕' },
            { key: 'reading', label: 'Reading', shortLabel: 'Reading', icon: '📖' },
            { key: 'finished', label: 'Finished', shortLabel: 'Done', icon: '🏆' },
          ].map(({ key, label, shortLabel, icon }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`px-3 py-2 sm:px-4 sm:py-2.5 rounded-full font-semibold transition-all flex items-center gap-1.5 whitespace-nowrap min-h-[44px] shrink-0 text-sm sm:text-base ${
                filter === key
                  ? 'bg-white shadow-lg text-purple-600 scale-105'
                  : 'bg-white/50 text-gray-600 hover:bg-white/80 active:bg-white'
              }`}
            >
              <span>{icon}</span>
              <span className="hidden sm:inline">{label}</span>
              <span className="sm:hidden">{shortLabel}</span>
            </button>
          ))}
        </div>
        
        {/* Story Grid - 2 cols mobile, 3 cols tablet, 4 cols large tablet/desktop */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 sm:gap-4 lg:gap-5">
          {filteredStories.map((story, index) => (
            <StoryCard key={story.id} story={story} index={index} />
          ))}
        </div>
        
        {/* Empty state */}
        {filteredStories.length === 0 && (
          <div className="text-center py-10 sm:py-12 lg:py-16">
            <div className="text-4xl sm:text-5xl lg:text-6xl mb-3 sm:mb-4">📭</div>
            <h3 className="text-lg sm:text-xl lg:text-2xl font-bold text-gray-700 mb-2" style={{ fontFamily: "'Nunito', sans-serif" }}>
              No stories here yet!
            </h3>
            <p className="text-gray-500 text-sm sm:text-base">Try a different filter or create a new adventure!</p>
          </div>
        )}
        
        {/* Footer encouragement - compact */}
        <div className="mt-6 sm:mt-8 lg:mt-10 text-center">
          <div className="inline-flex items-center gap-2 bg-white/60 backdrop-blur-sm rounded-xl px-4 py-2.5 sm:px-5 sm:py-3 shadow-sm">
            <span className="text-xl sm:text-2xl">🌟</span>
            <p className="text-gray-600 font-medium text-xs sm:text-sm lg:text-base" style={{ fontFamily: "'Nunito', sans-serif" }}>
              You've finished <span className="text-purple-600 font-bold">{finishedCount}</span> {finishedCount === 1 ? 'story' : 'stories'}! Keep reading!
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
