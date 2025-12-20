/**
 * Error Screen
 * 
 * PRODUCTION SETUP:
 * 1. Move @keyframes (float, wiggle, shake, bounce) to tailwind.config.js under theme.extend.keyframes
 * 2. Add corresponding animation utilities under theme.extend.animation
 * 3. Move Google Fonts import to <head> or configure via next/font (Next.js)
 * 4. Connect onRetry and onGoBack props to actual navigation/retry logic
 * 5. Pass appropriate errorType prop based on the actual error encountered
 */

import { useState, useEffect } from 'react';

const errorContent = {
  creation: {
    emoji: '🧙‍♂️',
    title: "Oops! The magic fizzled out",
    message: "Our story wizard got a little confused. Let's try making your story again!",
    retryLabel: "Try Again",
    showRetry: true,
  },
  network: {
    emoji: '🌧️',
    title: "Oh no! We lost connection",
    message: "It looks like the internet clouds floated away. Check your connection and try again!",
    retryLabel: "Try Again",
    showRetry: true,
  },
  notFound: {
    emoji: '🗺️',
    title: "Hmm, we can't find that",
    message: "This story seems to have wandered off on its own adventure. Let's go back and find another!",
    retryLabel: null,
    showRetry: false,
  },
  generic: {
    emoji: '🤔',
    title: "Something went wrong",
    message: "Even wizards make mistakes sometimes! Let's try that again.",
    retryLabel: "Try Again",
    showRetry: true,
  },
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

function SadSparkles() {
  return (
    <div className="absolute inset-0 pointer-events-none" style={{ margin: '-2rem' }}>
      <div className="absolute top-0 left-1/4 text-2xl opacity-50" style={{ animation: 'float 3s ease-in-out infinite' }}>✨</div>
      <div className="absolute top-1/4 right-0 text-xl opacity-40" style={{ animation: 'float 4s ease-in-out 0.5s infinite' }}>⭐</div>
      <div className="absolute bottom-1/4 left-0 text-xl opacity-40" style={{ animation: 'float 3.5s ease-in-out 1s infinite' }}>✨</div>
      <div className="absolute bottom-0 right-1/4 text-2xl opacity-50" style={{ animation: 'float 4s ease-in-out 1.5s infinite' }}>💫</div>
    </div>
  );
}

export default function ErrorScreen({ 
  errorType = 'generic', 
  onRetry = () => {}, 
  onGoBack = () => {} 
}) {
  const [wiggle, setWiggle] = useState(false);
  const content = errorContent[errorType] || errorContent.generic;
  
  // Trigger a little wiggle animation periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setWiggle(true);
      setTimeout(() => setWiggle(false), 500);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-100 via-purple-50 to-pink-100 relative overflow-hidden">
      {/* CSS */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&family=Baloo+2:wght@700;800&display=swap');
        
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-15px) rotate(3deg); }
        }
        
        @keyframes wiggle {
          0%, 100% { transform: rotate(0deg); }
          25% { transform: rotate(-10deg); }
          75% { transform: rotate(10deg); }
        }
        
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-5px); }
          75% { transform: translateX(5px); }
        }
        
        @keyframes bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }
        
        .wiggle-animation {
          animation: wiggle 0.5s ease-in-out;
        }
        
        .retry-btn:hover {
          animation: bounce 0.5s ease-in-out infinite;
        }
        
        .retry-btn:active {
          transform: scale(0.95);
        }
      `}</style>
      
      {/* Floating decorations - more elements, better distributed */}
      <FloatingElement delay={0} duration={4} className="top-[10%] left-[10%] text-2xl opacity-30">🌙</FloatingElement>
      <FloatingElement delay={1.5} duration={5} className="top-[15%] right-[15%] text-xl opacity-25">⭐</FloatingElement>
      <FloatingElement delay={0.5} duration={4.5} className="top-[30%] left-[5%] text-lg opacity-20">✨</FloatingElement>
      <FloatingElement delay={2} duration={4} className="top-[25%] right-[8%] text-2xl opacity-25">💫</FloatingElement>
      <FloatingElement delay={1} duration={5.5} className="bottom-[35%] left-[8%] text-xl opacity-25">⭐</FloatingElement>
      <FloatingElement delay={2.5} duration={4.5} className="bottom-[25%] right-[10%] text-lg opacity-20">✨</FloatingElement>
      <FloatingElement delay={0.8} duration={5} className="bottom-[15%] left-[15%] text-2xl opacity-30">🌟</FloatingElement>
      <FloatingElement delay={1.8} duration={4} className="bottom-[10%] right-[20%] text-xl opacity-25">💫</FloatingElement>
      <FloatingElement delay={3} duration={5} className="top-[50%] left-[3%] text-lg opacity-20">⭐</FloatingElement>
      <FloatingElement delay={2.2} duration={4.5} className="top-[45%] right-[5%] text-xl opacity-20">✨</FloatingElement>
      
      {/* Main container */}
      <div className="relative z-10 max-w-lg mx-auto px-4 sm:px-6 py-8 min-h-screen flex flex-col items-center justify-center">
        
        {/* Error illustration */}
        <div className="relative mb-10">
          <SadSparkles />
          <div 
            className={`leading-none ${wiggle ? 'wiggle-animation' : ''}`}
            style={{ 
              fontSize: '10rem',
              filter: 'drop-shadow(0 8px 16px rgba(0,0,0,0.15))',
            }}
          >
            {content.emoji}
          </div>
        </div>
        
        {/* Error message - floating text */}
        <div className="text-center max-w-md w-full mb-8">
          <h1 
            className="text-2xl sm:text-3xl font-bold text-gray-800 mb-3"
            style={{ fontFamily: "'Baloo 2', cursive" }}
          >
            {content.title}
          </h1>
          <p 
            className="text-gray-600 text-base sm:text-lg leading-relaxed"
            style={{ fontFamily: "'Nunito', sans-serif" }}
          >
            {content.message}
          </p>
        </div>
        
        {/* Action buttons */}
        <div className="flex flex-col sm:flex-row gap-3 w-full max-w-md">
          {content.showRetry && (
            <button
              onClick={onRetry}
              className="retry-btn flex-1 bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500 text-white font-bold py-4 px-6 rounded-2xl shadow-lg hover:shadow-xl transition-shadow flex items-center justify-center gap-2 min-h-[56px]"
              style={{ fontFamily: "'Nunito', sans-serif" }}
            >
              <span className="text-xl">🔄</span>
              <span className="text-lg">{content.retryLabel}</span>
            </button>
          )}
          
          <button
            onClick={onGoBack}
            className={`flex-1 bg-white/80 backdrop-blur-sm text-gray-700 font-bold py-4 px-6 rounded-2xl shadow-lg hover:bg-white hover:shadow-xl transition-all flex items-center justify-center gap-2 min-h-[56px] ${!content.showRetry ? 'bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500 text-white' : ''}`}
            style={{ fontFamily: "'Nunito', sans-serif" }}
          >
            <span className="text-xl">🏠</span>
            <span className="text-lg">Go Home</span>
          </button>
        </div>
        
        {/* Encouraging footer */}
        <div className="mt-10 text-center">
          <p 
            className="text-gray-400 text-sm"
            style={{ fontFamily: "'Nunito', sans-serif" }}
          >
            Don't worry, your magical adventures await! ✨
          </p>
        </div>
      </div>
    </div>
  );
}
