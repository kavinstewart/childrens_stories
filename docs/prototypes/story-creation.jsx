/**
 * Story Creation Loading Screen
 * 
 * PRODUCTION SETUP:
 * 1. Move @keyframes (float, wizardBob, particle, firefly, stageIcon, completePop) to tailwind.config.js
 * 2. Add corresponding animation utilities under theme.extend.animation
 * 3. Move Google Fonts import to <head> or configure via next/font (Next.js)
 * 4. Replace simulated stage progression with actual API progress callbacks
 * 5. The wizard uses inline fontSize: '10rem' for preview compatibility - can use text-[10rem] with Tailwind JIT
 * 6. Adjust stage durations to match actual story generation time
 */

import { useState, useEffect } from 'react';

const creationStages = [
  { message: "Opening the story vault", icon: "📖", duration: 2500 },
  { message: "Gathering magical ingredients", icon: "✨", duration: 2000 },
  { message: "Waking up the characters", icon: "🌟", duration: 2500 },
  { message: "Sprinkling in some adventure", icon: "🗺️", duration: 2000 },
  { message: "Mixing in a pinch of wonder", icon: "🔮", duration: 2500 },
  { message: "Painting the scenes", icon: "🎨", duration: 2000 },
  { message: "Adding a twist", icon: "🌀", duration: 2500 },
  { message: "Polishing the ending", icon: "💎", duration: 2000 },
  { message: "Your story is ready!", icon: "🎉", duration: 0 },
];

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

function Wizard({ stage }) {
  const storyEmojis = [
    // Wizards - all variants
    '🧙', '🧙‍♂️', '🧙‍♀️', '🧙🏻', '🧙🏼', '🧙🏽', '🧙🏾', '🧙🏿',
    '🧙🏻‍♂️', '🧙🏼‍♂️', '🧙🏽‍♂️', '🧙🏾‍♂️', '🧙🏿‍♂️',
    '🧙🏻‍♀️', '🧙🏼‍♀️', '🧙🏽‍♀️', '🧙🏾‍♀️', '🧙🏿‍♀️',
    // Fairies - all variants
    '🧚', '🧚‍♂️', '🧚‍♀️', '🧚🏻', '🧚🏼', '🧚🏽', '🧚🏾', '🧚🏿',
    '🧚🏻‍♀️', '🧚🏼‍♀️', '🧚🏽‍♀️', '🧚🏾‍♀️', '🧚🏿‍♀️',
    // Royalty - all variants
    '🤴', '🤴🏻', '🤴🏼', '🤴🏽', '🤴🏾', '🤴🏿',
    '👸', '👸🏻', '👸🏼', '👸🏽', '👸🏾', '👸🏿',
    // Superheroes - all variants
    '🦸', '🦸‍♂️', '🦸‍♀️', '🦸🏻', '🦸🏼', '🦸🏽', '🦸🏾', '🦸🏿',
    '🦸🏻‍♂️', '🦸🏼‍♂️', '🦸🏽‍♂️', '🦸🏾‍♂️', '🦸🏿‍♂️',
    '🦸🏻‍♀️', '🦸🏼‍♀️', '🦸🏽‍♀️', '🦸🏾‍♀️', '🦸🏿‍♀️',
    // Children - all variants
    '🧒', '🧒🏻', '🧒🏼', '🧒🏽', '🧒🏾', '🧒🏿',
    '👦', '👦🏻', '👦🏼', '👦🏽', '👦🏾', '👦🏿',
    '👧', '👧🏻', '👧🏼', '👧🏽', '👧🏾', '👧🏿',
    // Magical creatures
    '🦄', '🐉', '🐲', '🧜‍♀️', '🧜‍♂️', '🧞', '🧞‍♂️', '🧞‍♀️',
    // Cute animals (story characters)
    '🐻', '🦁', '🐰', '🦊', '🐸', '🐢', '🦉', '🐧', '🐨', '🐼', 
    '🦋', '🐱', '🐶', '🐭', '🐹', '🦔', '🐿️',
    // Storybook items
    '📖', '🪄', '🔮', '👑', '🏰', '🌈', '⭐', '🌙', '✨', '💫'
  ];
  
  const [currentEmoji, setCurrentEmoji] = useState(storyEmojis[0]);
  
  useEffect(() => {
    const interval = setInterval(() => {
      const randomIndex = Math.floor(Math.random() * storyEmojis.length);
      setCurrentEmoji(storyEmojis[randomIndex]);
    }, 600);
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div className="relative">
      {/* Wizard - use text-[10rem] in production Tailwind, inline style for preview compatibility */}
      <div 
        className="leading-none transition-transform duration-300 drop-shadow-2xl"
        style={{ 
          fontSize: '10rem',
          animation: 'wizardBob 1s ease-in-out infinite'
        }}
      >
        {currentEmoji}
      </div>
      
      {/* Magic particles around wizard */}
      <div className="absolute -top-8 -left-8 text-3xl" style={{ animation: 'particle 2s ease-in-out infinite' }}>✨</div>
      <div className="absolute -top-6 -right-10 text-2xl" style={{ animation: 'particle 2s ease-in-out infinite 0.5s' }}>⭐</div>
      <div className="absolute -bottom-6 -left-10 text-2xl" style={{ animation: 'particle 2s ease-in-out infinite 1s' }}>✨</div>
      <div className="absolute bottom-8 -right-8 text-3xl" style={{ animation: 'particle 2s ease-in-out infinite 1.5s' }}>🌟</div>
    </div>
  );
}

function Firefly({ delay, startX, startY }) {
  return (
    <div 
      className="absolute w-2 h-2 bg-yellow-300 rounded-full"
      style={{
        left: startX,
        top: startY,
        animation: `firefly 3s ease-in-out ${delay}s infinite`,
        boxShadow: '0 0 8px 2px rgba(253, 224, 71, 0.6)'
      }}
    />
  );
}

export default function StoryCreation() {
  const [currentStage, setCurrentStage] = useState(0);
  const [progress, setProgress] = useState(0);
  const [stageProgress, setStageProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  
  // User's input (would come from previous screen)
  const userPrompt = "A brave penguin who's afraid of water";
  const selectedTheme = { label: "Bravery", icon: "🦁", color: "from-amber-400 to-orange-500" };
  
  // Progress through stages
  useEffect(() => {
    if (currentStage >= creationStages.length - 1) {
      setIsComplete(true);
      return;
    }
    
    const stage = creationStages[currentStage];
    const interval = 50;
    const steps = stage.duration / interval;
    let step = 0;
    
    const timer = setInterval(() => {
      step++;
      setStageProgress((step / steps) * 100);
      
      if (step >= steps) {
        clearInterval(timer);
        setCurrentStage(prev => prev + 1);
        setStageProgress(0);
        setProgress(((currentStage + 1) / (creationStages.length - 1)) * 100);
      }
    }, interval);
    
    return () => clearInterval(timer);
  }, [currentStage]);
  
  const stage = creationStages[currentStage];

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-200 via-purple-100 to-pink-200 relative overflow-hidden">
      {/* CSS */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&family=Baloo+2:wght@700;800&display=swap');
        
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-15px) rotate(3deg); }
        }
        
        @keyframes wizardBob {
          0%, 100% { transform: translateY(0) rotate(-2deg); }
          50% { transform: translateY(-8px) rotate(2deg); }
        }
        
        @keyframes particle {
          0%, 100% { transform: translateY(0) scale(1); opacity: 0.7; }
          50% { transform: translateY(-10px) scale(1.2); opacity: 1; }
        }
        
        @keyframes firefly {
          0% { transform: translate(0, 0) scale(1); opacity: 0.3; }
          25% { transform: translate(15px, -20px) scale(1.2); opacity: 1; }
          50% { transform: translate(-10px, -35px) scale(0.8); opacity: 0.6; }
          75% { transform: translate(20px, -15px) scale(1.1); opacity: 0.9; }
          100% { transform: translate(0, 0) scale(1); opacity: 0.3; }
        }
        
        @keyframes stageIcon {
          0% { transform: scale(0) rotate(-180deg); opacity: 0; }
          50% { transform: scale(1.3) rotate(10deg); opacity: 1; }
          100% { transform: scale(1) rotate(0deg); opacity: 1; }
        }
        
        @keyframes completePop {
          0% { transform: scale(0); }
          50% { transform: scale(1.2); }
          100% { transform: scale(1); }
        }
        
        @keyframes confetti {
          0% { transform: translateY(0) rotate(0deg); opacity: 1; }
          100% { transform: translateY(100px) rotate(720deg); opacity: 0; }
        }
        
        .stage-icon {
          animation: stageIcon 0.5s ease-out forwards;
        }
      `}</style>
      
      {/* Floating decorations */}
      <FloatingElement delay={1.5} duration={5} className="top-24 right-12 text-xl opacity-30">⭐</FloatingElement>
      <FloatingElement delay={0.5} duration={4.5} className="bottom-32 left-12 text-2xl opacity-35">🌙</FloatingElement>
      <FloatingElement delay={2} duration={5} className="bottom-24 right-8 text-xl opacity-30">✨</FloatingElement>
      
      {/* Fireflies */}
      <Firefly delay={0} startX="20%" startY="30%" />
      <Firefly delay={0.8} startX="70%" startY="25%" />
      <Firefly delay={1.5} startX="15%" startY="60%" />
      <Firefly delay={2.2} startX="80%" startY="55%" />
      <Firefly delay={0.5} startX="50%" startY="70%" />
      
      {/* Main container */}
      <div className="relative z-10 max-w-xl mx-auto px-4 sm:px-6 pt-12 pb-8 min-h-screen flex flex-col items-center justify-center">
        
        {/* User's prompt echo - subdued */}
        <div className="w-full bg-white/40 backdrop-blur-sm rounded-2xl p-3 mb-16 text-center">
          <p className="text-gray-400 text-xs mb-0.5" style={{ fontFamily: "'Nunito', sans-serif" }}>
            Creating a story about...
          </p>
          <p className="text-gray-600 font-semibold text-base" style={{ fontFamily: "'Nunito', sans-serif" }}>
            "{userPrompt}"
          </p>
          {selectedTheme && (
            <div className="inline-flex items-center gap-1 mt-1.5 px-2.5 py-0.5 bg-gradient-to-r from-amber-400 to-orange-500 rounded-full">
              <span className="text-sm">{selectedTheme.icon}</span>
              <span className="text-white text-xs font-semibold" style={{ fontFamily: "'Nunito', sans-serif" }}>
                {selectedTheme.label}
              </span>
            </div>
          )}
        </div>
        
        {/* Main animation area - single centered focal point */}
        <div className="flex flex-col items-center w-full max-w-sm">
          {/* Wizard - the star of the show */}
          <div className="mb-10">
            <Wizard stage={currentStage} />
          </div>
          
          {/* Current stage message - floating text */}
          <div className="flex items-center justify-center gap-3 mb-8">
            <span 
              className="text-4xl stage-icon" 
              key={currentStage}
            >
              {stage.icon}
            </span>
            <span 
              className="text-gray-600 font-bold text-xl sm:text-2xl"
              style={{ fontFamily: "'Nunito', sans-serif" }}
            >
              {stage.message}
              {!isComplete && <span className="inline-block animate-pulse">...</span>}
            </span>
          </div>
          
          {/* Progress bar */}
          <div className="w-full mb-5">
            <div className="h-3 bg-white/50 rounded-full overflow-hidden shadow-inner">
              <div 
                className="h-full bg-gradient-to-r from-purple-500 via-pink-500 to-amber-400 rounded-full transition-[width] duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
          
          {/* Stage history (completed stages) - fixed height to prevent layout shift */}
          <div className="flex justify-center gap-2 w-full h-10">
            {creationStages.slice(0, currentStage).map((s, i) => (
              <div 
                key={i}
                className="w-9 h-9 bg-white/70 rounded-full flex items-center justify-center shadow-sm"
                title={s.message}
              >
                <span className="text-base">{s.icon}</span>
              </div>
            ))}
          </div>
        </div>
        
        {/* Completion state */}
        {isComplete && (
          <div className="mt-10" style={{ animation: 'completePop 0.5s ease-out' }}>
            <button
              className="bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500 text-white font-bold py-4 px-8 rounded-2xl shadow-lg hover:shadow-xl hover:scale-105 active:scale-95 transition-all flex items-center gap-3 min-h-[56px]"
              style={{ fontFamily: "'Nunito', sans-serif" }}
            >
              <span className="text-2xl">📖</span>
              <span className="text-lg">Read Your Story!</span>
              <span className="text-2xl">✨</span>
            </button>
          </div>
        )}
        
        {/* Cancel link (only while loading) */}
        {!isComplete && (
          <button 
            className="mt-10 text-gray-400 hover:text-gray-600 text-sm font-medium transition-colors"
            style={{ fontFamily: "'Nunito', sans-serif" }}
          >
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}
