/**
 * Story Reader Screen
 * 
 * PRODUCTION SETUP:
 * 1. Move @keyframes (float, pageIn, pulse-soft) to tailwind.config.js under theme.extend.keyframes
 * 2. Add corresponding animation utilities under theme.extend.animation
 * 3. Move Google Fonts import to <head> or configure via next/font (Next.js)
 * 4. scrollbar-hide can be added via tailwind-scrollbar-hide plugin
 * 5. The .page-content and .nav-btn classes can become Tailwind utilities or component classes
 */

import { useState } from 'react';

const storyData = {
  title: "The Bear Who Shared",
  theme: "sharing",
  totalPages: 32,
  color: "from-amber-400 to-orange-500",
  accent: "#f59e0b",
  pages: [
    {
      id: 1,
      illustration: "🏔️",
      illustrationBg: "from-sky-300 to-blue-400",
      text: "Once upon a time, in a cozy cave high up in the mountains, there lived a little bear named Bruno."
    },
    {
      id: 2,
      illustration: "🐻",
      illustrationBg: "from-amber-300 to-orange-400",
      text: "Bruno loved honey more than anything in the whole wide world. He had jars and jars of golden, sticky honey stacked all around his cave."
    },
    {
      id: 3,
      illustration: "🍯",
      illustrationBg: "from-yellow-300 to-amber-400",
      text: '"All mine!" Bruno would say, hugging his honey jars tight. "Every last drop is mine, mine, mine!"'
    },
    {
      id: 4,
      illustration: "🐰",
      illustrationBg: "from-pink-300 to-rose-400",
      text: "One sunny morning, a little rabbit named Rosie came hopping by. She looked tired and hungry from her long journey."
    },
    {
      id: 5,
      illustration: "🥺",
      illustrationBg: "from-purple-300 to-violet-400",
      text: '"Excuse me, Mr. Bear," said Rosie softly. "Could you spare just a tiny bit of honey? I haven\'t eaten all day."'
    },
    {
      id: 6,
      illustration: "😤",
      illustrationBg: "from-red-300 to-orange-400",
      text: "Bruno frowned and shook his head. \"No way! This honey is all mine. Go find your own!\" And he slammed his cave door shut."
    },
    {
      id: 7,
      illustration: "🌧️",
      illustrationBg: "from-slate-400 to-gray-500",
      text: "That night, a terrible storm came. Thunder rumbled and rain poured down. Bruno heard a tiny knock at his door."
    },
    {
      id: 8,
      illustration: "💕",
      illustrationBg: "from-pink-400 to-rose-500",
      text: "It was Rosie, shivering and cold. This time, Bruno felt something warm in his heart. He opened the door wide and said, \"Come in, friend.\""
    }
  ]
};

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

export default function StoryReader() {
  const [currentPage, setCurrentPage] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [fontSize, setFontSize] = useState('large'); // 'medium', 'large', 'xlarge'
  
  const page = storyData.pages[currentPage];
  const progress = ((currentPage + 1) / storyData.pages.length) * 100;
  
  const goToPage = (newPage) => {
    if (newPage < 0 || newPage >= storyData.pages.length || isAnimating) return;
    setIsAnimating(true);
    setTimeout(() => {
      setCurrentPage(newPage);
      setIsAnimating(false);
    }, 150);
  };
  
  const fontSizeClasses = {
    medium: 'text-lg sm:text-xl',
    large: 'text-xl sm:text-2xl',
    xlarge: 'text-2xl sm:text-3xl'
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-100 via-purple-50 to-pink-100 relative overflow-hidden">
      {/* CSS */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&family=Baloo+2:wght@700;800&display=swap');
        
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-15px) rotate(3deg); }
        }
        
        @keyframes pageIn {
          from {
            opacity: 0;
            transform: scale(0.95);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }
        
        @keyframes pulse-soft {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.05); }
        }
        
        .page-content {
          animation: pageIn 0.3s ease-out;
        }
        
        .nav-btn:active {
          transform: scale(0.95);
        }
        
        .scrollbar-hide {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
      `}</style>
      
      {/* Floating decorations */}
      <FloatingElement delay={0} duration={4} className="top-20 left-6 text-2xl opacity-30 hidden sm:block">✨</FloatingElement>
      <FloatingElement delay={1.5} duration={5} className="top-32 right-8 text-xl opacity-25 hidden sm:block">⭐</FloatingElement>
      <FloatingElement delay={0.5} duration={4.5} className="bottom-32 left-8 text-xl opacity-25 hidden md:block">🌟</FloatingElement>
      
      {/* Main container */}
      <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 py-4 sm:py-6 min-h-screen flex flex-col">
        
        {/* Top bar */}
        <div className="flex items-center justify-between gap-3 mb-4 sm:mb-6">
          {/* Back button */}
          <button className="flex items-center gap-2 bg-white/70 hover:bg-white/90 active:scale-95 backdrop-blur-sm rounded-xl px-3 py-2.5 sm:px-4 sm:py-3 shadow-sm transition-all min-h-[44px]">
            <span className="text-lg">←</span>
            <span className="text-gray-700 font-semibold text-sm sm:text-base hidden sm:inline" style={{ fontFamily: "'Nunito', sans-serif" }}>Library</span>
          </button>
          
          {/* Story title */}
          <div className="flex-1 text-center">
            <h1 
              className="text-lg sm:text-xl lg:text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-amber-500 to-orange-500 truncate px-2"
              style={{ fontFamily: "'Baloo 2', cursive" }}
            >
              {storyData.title}
            </h1>
          </div>
          
          {/* Settings button */}
          <button 
            onClick={() => setShowSettings(!showSettings)}
            className="flex items-center gap-2 bg-white/70 hover:bg-white/90 active:scale-95 backdrop-blur-sm rounded-xl px-3 py-2.5 sm:px-4 sm:py-3 shadow-sm transition-all min-h-[44px]"
          >
            <span className="text-lg">⚙️</span>
          </button>
        </div>
        
        {/* Settings dropdown */}
        {showSettings && (
          <div className="absolute top-16 right-4 sm:right-6 z-20 bg-white rounded-2xl shadow-xl p-4 w-64" style={{ fontFamily: "'Nunito', sans-serif" }}>
            <div className="font-bold text-gray-700 mb-3">Text Size</div>
            <div className="flex gap-2">
              {[
                { key: 'medium', label: 'A', size: 'text-sm' },
                { key: 'large', label: 'A', size: 'text-lg' },
                { key: 'xlarge', label: 'A', size: 'text-2xl' }
              ].map(({ key, label, size }) => (
                <button
                  key={key}
                  onClick={() => setFontSize(key)}
                  className={`flex-1 py-2 rounded-xl font-bold transition-all ${size} ${
                    fontSize === key 
                      ? 'bg-amber-500 text-white shadow-md' 
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        )}
        
        {/* Progress bar */}
        <div className="mb-4 sm:mb-6">
          <div className="flex items-center gap-3 mb-1.5">
            <div className="flex-1 h-2 bg-white/50 rounded-full overflow-hidden shadow-inner">
              <div 
                className="h-full bg-gradient-to-r from-amber-400 to-orange-500 rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-sm font-semibold text-gray-500 whitespace-nowrap" style={{ fontFamily: "'Nunito', sans-serif" }}>
              {currentPage + 1} / {storyData.pages.length}
            </span>
          </div>
        </div>
        
        {/* Main content area - always side-by-side */}
        <div className="flex-1 flex flex-row gap-4 mb-4">
          
          {/* Illustration panel */}
          <div 
            className={`relative rounded-3xl overflow-hidden shadow-xl w-1/2 min-h-[200px] bg-gradient-to-br ${page.illustrationBg} ${isAnimating ? 'opacity-50' : 'opacity-100'} transition-opacity duration-150`}
          >
            {/* Decorative shapes */}
            <div className="absolute -top-10 -right-10 w-32 h-32 bg-white/10 rounded-full" />
            <div className="absolute -bottom-10 -left-10 w-40 h-40 bg-white/10 rounded-full" />
            <div className="absolute top-1/4 right-1/4 w-20 h-20 bg-white/5 rounded-full" />
            
            {/* Main illustration */}
            <div 
              className="absolute inset-0 flex items-center justify-center page-content"
              key={currentPage}
            >
              <span 
                className="text-6xl sm:text-7xl lg:text-8xl"
                style={{ filter: 'drop-shadow(0 8px 16px rgba(0,0,0,0.2))' }}
              >
                {page.illustration}
              </span>
            </div>
            
            {/* Page number badge */}
            <div className="absolute bottom-3 right-3 bg-white/80 backdrop-blur-sm rounded-full px-3 py-1 shadow-md">
              <span className="text-xs font-bold text-gray-600" style={{ fontFamily: "'Nunito', sans-serif" }}>
                Page {page.id}
              </span>
            </div>
          </div>
          
          {/* Text panel */}
          <div className="w-1/2 flex flex-col">
            <div 
              className={`flex-1 bg-white/80 backdrop-blur-sm rounded-3xl shadow-lg p-5 sm:p-6 lg:p-8 flex items-center ${isAnimating ? 'opacity-50' : 'opacity-100'} transition-opacity duration-150`}
            >
              <p 
                className={`${fontSizeClasses[fontSize]} text-gray-800 leading-relaxed page-content`}
                style={{ fontFamily: "'Nunito', sans-serif" }}
                key={currentPage}
              >
                {page.text}
              </p>
            </div>
          </div>
        </div>
        
        {/* Navigation controls */}
        <div className="flex items-center justify-between gap-4">
          {/* Previous button */}
          <button 
            onClick={() => goToPage(currentPage - 1)}
            disabled={currentPage === 0}
            className={`nav-btn flex items-center gap-2 bg-white/80 backdrop-blur-sm rounded-2xl px-4 py-3 sm:px-6 sm:py-4 shadow-lg transition-all min-h-[56px] ${
              currentPage === 0 
                ? 'opacity-40 cursor-not-allowed' 
                : 'hover:bg-white hover:shadow-xl active:scale-95'
            }`}
          >
            <span className="text-2xl">👈</span>
            <span className="text-gray-700 font-bold text-sm sm:text-base hidden sm:inline" style={{ fontFamily: "'Nunito', sans-serif" }}>Back</span>
          </button>
          
          {/* Page dots - horizontal scroll on mobile */}
          <div className="flex-1 flex justify-center">
            <div className="flex gap-1.5 sm:gap-2 overflow-x-auto scrollbar-hide px-2 py-1">
              {storyData.pages.map((_, index) => (
                <button
                  key={index}
                  onClick={() => goToPage(index)}
                  className={`w-2.5 h-2.5 sm:w-3 sm:h-3 rounded-full transition-all shrink-0 ${
                    index === currentPage 
                      ? 'bg-gradient-to-r from-amber-400 to-orange-500 scale-125 shadow-md' 
                      : index < currentPage
                        ? 'bg-amber-300 hover:bg-amber-400'
                        : 'bg-gray-300 hover:bg-gray-400'
                  }`}
                />
              ))}
            </div>
          </div>
          
          {/* Next button */}
          <button 
            onClick={() => goToPage(currentPage + 1)}
            disabled={currentPage === storyData.pages.length - 1}
            className={`nav-btn flex items-center gap-2 bg-gradient-to-r from-amber-400 to-orange-500 rounded-2xl px-4 py-3 sm:px-6 sm:py-4 shadow-lg transition-all min-h-[56px] ${
              currentPage === storyData.pages.length - 1 
                ? 'opacity-40 cursor-not-allowed' 
                : 'hover:shadow-xl hover:scale-105 active:scale-95'
            }`}
          >
            <span className="text-white font-bold text-sm sm:text-base hidden sm:inline" style={{ fontFamily: "'Nunito', sans-serif" }}>Next</span>
            <span className="text-2xl">👉</span>
          </button>
        </div>
        
        {/* Completion celebration (shown on last page) */}
        {currentPage === storyData.pages.length - 1 && (
          <div className="mt-4 sm:mt-6 text-center">
            <div 
              className="inline-flex items-center gap-3 bg-gradient-to-r from-yellow-400 to-amber-500 rounded-2xl px-5 py-3 shadow-lg"
              style={{ animation: 'pulse-soft 2s ease-in-out infinite' }}
            >
              <span className="text-2xl">🎉</span>
              <span className="text-white font-bold" style={{ fontFamily: "'Nunito', sans-serif" }}>
                You finished the story!
              </span>
              <span className="text-2xl">🎉</span>
            </div>
          </div>
        )}
      </div>
      
      {/* Click outside to close settings */}
      {showSettings && (
        <div 
          className="fixed inset-0 z-10" 
          onClick={() => setShowSettings(false)}
        />
      )}
    </div>
  );
}
