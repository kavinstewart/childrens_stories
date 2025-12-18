import { useState, useEffect } from 'react';

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

export default function NewStory() {
  const [inputMode, setInputMode] = useState('text'); // 'text' or 'voice'
  const [storyPrompt, setStoryPrompt] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [voiceWaves, setVoiceWaves] = useState([0.3, 0.5, 0.7, 0.5, 0.3]);
  const [selectedTheme, setSelectedTheme] = useState(null);
  const [isCreating, setIsCreating] = useState(false);
  
  // Simulate voice wave animation when listening
  useEffect(() => {
    if (!isListening) return;
    
    const interval = setInterval(() => {
      setVoiceWaves(prev => prev.map(() => 0.2 + Math.random() * 0.8));
    }, 150);
    
    return () => clearInterval(interval);
  }, [isListening]);
  
  const themes = [
    { id: 'kindness', label: 'Kindness', icon: '💕', color: 'from-pink-400 to-rose-500' },
    { id: 'bravery', label: 'Bravery', icon: '🦁', color: 'from-amber-400 to-orange-500' },
    { id: 'sharing', label: 'Sharing', icon: '🤝', color: 'from-emerald-400 to-teal-500' },
    { id: 'creativity', label: 'Creativity', icon: '🎨', color: 'from-violet-400 to-purple-500' },
    { id: 'friendship', label: 'Friendship', icon: '🌟', color: 'from-sky-400 to-blue-500' },
    { id: 'patience', label: 'Patience', icon: '🐢', color: 'from-lime-400 to-green-500' },
  ];
  
  const toggleVoice = () => {
    if (inputMode === 'text') {
      setInputMode('voice');
      setIsListening(true);
    } else {
      setIsListening(!isListening);
    }
  };
  
  const switchToText = () => {
    setInputMode('text');
    setIsListening(false);
  };
  
  const handleCreate = () => {
    setIsCreating(true);
    // Simulate creation delay
    setTimeout(() => setIsCreating(false), 2000);
  };
  
  const canCreate = storyPrompt.trim().length > 0 || selectedTheme;

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-100 via-purple-50 to-pink-100 relative overflow-hidden">
      {/* CSS */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&family=Baloo+2:wght@700;800&display=swap');
        
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-15px) rotate(3deg); }
        }
        
        @keyframes pulse-ring {
          0% { transform: scale(1); opacity: 0.8; }
          100% { transform: scale(1.5); opacity: 0; }
        }
        
        @keyframes wiggle {
          0%, 100% { transform: rotate(-3deg); }
          50% { transform: rotate(3deg); }
        }
        
        @keyframes sparkle-pop {
          0% { transform: scale(0) rotate(0deg); opacity: 0; }
          50% { transform: scale(1.2) rotate(180deg); opacity: 1; }
          100% { transform: scale(1) rotate(360deg); opacity: 1; }
        }
        
        .create-btn:hover:not(:disabled) {
          animation: wiggle 0.3s ease-in-out infinite;
        }
        
        .theme-pill:active {
          transform: scale(0.95);
        }
        
        .voice-wave {
          transition: height 0.15s ease-out;
        }
      `}</style>
      
      {/* Floating decorations */}
      <FloatingElement delay={0} duration={4} className="top-20 left-6 text-2xl opacity-30 hidden sm:block">✨</FloatingElement>
      <FloatingElement delay={1} duration={5} className="top-32 right-8 text-xl opacity-25 hidden sm:block">📝</FloatingElement>
      <FloatingElement delay={2} duration={4.5} className="bottom-32 right-12 text-2xl opacity-30 hidden sm:block">🌈</FloatingElement>
      <FloatingElement delay={0.5} duration={5} className="bottom-24 left-10 text-xl opacity-25 hidden sm:block">💫</FloatingElement>
      
      {/* Main container */}
      <div className="relative z-10 max-w-2xl mx-auto px-4 sm:px-6 py-6 sm:py-8 min-h-screen flex flex-col">
        
        {/* Top bar */}
        <div className="flex items-center justify-between gap-3 mb-6">
          <button className="flex items-center gap-2 bg-white/70 hover:bg-white/90 active:scale-95 backdrop-blur-sm rounded-xl px-3 py-2.5 shadow-sm transition-all min-h-[44px]">
            <span className="text-lg">←</span>
            <span className="text-gray-700 font-semibold text-sm hidden sm:inline" style={{ fontFamily: "'Nunito', sans-serif" }}>Back</span>
          </button>
          
          <h1 
            className="text-2xl sm:text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-600 via-pink-500 to-orange-400"
            style={{ fontFamily: "'Baloo 2', cursive" }}
          >
            ✨ New Story
          </h1>
          
          <div className="w-[44px]" /> {/* Spacer for centering */}
        </div>
        
        {/* Main content */}
        <div className="flex-1 flex flex-col gap-5">
          
          {/* Prompt section */}
          <div className="bg-white/80 backdrop-blur-sm rounded-3xl shadow-lg p-5 sm:p-6">
            <label 
              className="block text-lg font-bold text-gray-700 mb-3"
              style={{ fontFamily: "'Nunito', sans-serif" }}
            >
              What should your story be about?
            </label>
            
            {/* Text input */}
            {inputMode === 'text' && (
              <div className="relative">
                <textarea
                  value={storyPrompt}
                  onChange={(e) => setStoryPrompt(e.target.value)}
                  placeholder="A brave little mouse who dreams of becoming a chef..."
                  className="w-full h-32 sm:h-40 bg-gray-50 rounded-2xl p-4 pr-14 text-gray-700 placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-purple-300 transition-all text-base sm:text-lg"
                  style={{ fontFamily: "'Nunito', sans-serif" }}
                />
                <button
                  onClick={() => { setInputMode('voice'); setIsListening(true); }}
                  className="absolute bottom-3 right-3 w-11 h-11 bg-white hover:bg-purple-100 rounded-full shadow-md flex items-center justify-center transition-all active:scale-95"
                  title="Switch to voice input"
                >
                  <span className="text-xl">🎤</span>
                </button>
              </div>
            )}
            
            {/* Voice input */}
            {inputMode === 'voice' && (
              <div className="relative bg-gray-50 rounded-2xl p-4 min-h-[128px] sm:min-h-[160px] flex flex-col items-center justify-center">
                {/* Mic button with pulse ring */}
                <div className="relative mb-3">
                  {isListening && (
                    <>
                      <div 
                        className="absolute inset-0 bg-purple-400 rounded-full"
                        style={{ animation: 'pulse-ring 1.5s ease-out infinite' }}
                      />
                      <div 
                        className="absolute inset-0 bg-purple-400 rounded-full"
                        style={{ animation: 'pulse-ring 1.5s ease-out infinite 0.5s' }}
                      />
                    </>
                  )}
                  <button
                    onClick={toggleVoice}
                    className={`relative w-16 h-16 rounded-full flex items-center justify-center shadow-lg transition-all active:scale-95 ${
                      isListening 
                        ? 'bg-gradient-to-br from-purple-500 to-pink-500' 
                        : 'bg-gray-200 hover:bg-gray-300'
                    }`}
                  >
                    <span className="text-2xl">🎤</span>
                  </button>
                </div>
                
                {/* Voice wave visualization */}
                {isListening && (
                  <div className="flex items-end gap-1 h-8 mb-2">
                    {voiceWaves.map((height, i) => (
                      <div
                        key={i}
                        className="voice-wave w-1.5 bg-gradient-to-t from-purple-500 to-pink-400 rounded-full"
                        style={{ height: `${height * 32}px` }}
                      />
                    ))}
                  </div>
                )}
                
                <p 
                  className={`text-center text-sm font-semibold ${isListening ? 'text-purple-600' : 'text-gray-500'}`}
                  style={{ fontFamily: "'Nunito', sans-serif" }}
                >
                  {isListening ? "Listening... tell me your idea!" : 'Tap to start'}
                </p>
                
                {/* Keyboard button to switch back */}
                <button
                  onClick={switchToText}
                  className="absolute bottom-3 right-3 w-11 h-11 bg-white hover:bg-purple-100 rounded-full shadow-md flex items-center justify-center transition-all active:scale-95"
                  title="Switch to text input"
                >
                  <span className="text-xl">⌨️</span>
                </button>
              </div>
            )}
          </div>
          
          {/* Theme selection */}
          <div className="bg-white/80 backdrop-blur-sm rounded-3xl shadow-lg p-5 sm:p-6">
            <label 
              className="block text-lg font-bold text-gray-700 mb-3"
              style={{ fontFamily: "'Nunito', sans-serif" }}
            >
              Pick a lesson to learn <span className="font-normal text-gray-400">(optional)</span>
            </label>
            
            <div className="flex flex-wrap gap-2">
              {themes.map((theme) => (
                <button
                  key={theme.id}
                  onClick={() => setSelectedTheme(selectedTheme === theme.id ? null : theme.id)}
                  className={`theme-pill flex items-center gap-2 px-4 py-2.5 rounded-full font-semibold transition-all min-h-[44px] ${
                    selectedTheme === theme.id
                      ? `bg-gradient-to-r ${theme.color} text-white shadow-md scale-105`
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                  style={{ fontFamily: "'Nunito', sans-serif" }}
                >
                  <span>{theme.icon}</span>
                  <span>{theme.label}</span>
                </button>
              ))}
            </div>
          </div>
          
          {/* Inspiration prompt */}
          <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-2xl p-4 border border-amber-200/50">
            <div className="flex items-start gap-3">
              <span className="text-2xl">💡</span>
              <div style={{ fontFamily: "'Nunito', sans-serif" }}>
                <p className="font-semibold text-amber-700 mb-1">Need inspiration?</p>
                <p className="text-amber-600 text-sm">Try: "A penguin who's afraid of water" or "Two best friends on a treasure hunt"</p>
              </div>
            </div>
          </div>
        </div>
        
        {/* Create button - sticky at bottom */}
        <div className="pt-4 pb-2">
          <button
            onClick={handleCreate}
            disabled={!canCreate || isCreating}
            className={`create-btn w-full py-4 rounded-2xl font-bold text-lg shadow-lg transition-all min-h-[56px] flex items-center justify-center gap-3 ${
              canCreate && !isCreating
                ? 'bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500 text-white hover:shadow-xl active:scale-[0.98]'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
            style={{ fontFamily: "'Nunito', sans-serif" }}
          >
            {isCreating ? (
              <>
                <span className="text-xl animate-spin">✨</span>
                <span>Creating your story...</span>
              </>
            ) : (
              <>
                <span className="text-xl">🪄</span>
                <span>Create My Story</span>
              </>
            )}
          </button>
          
          {!canCreate && (
            <p className="text-center text-gray-400 text-sm mt-2" style={{ fontFamily: "'Nunito', sans-serif" }}>
              Tell me about your story or pick a theme to get started
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
