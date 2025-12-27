// Pill colors - vibrant, child-friendly palette
export const pillColors = [
  { bg: '#FEE2E2', border: '#FECACA', text: '#DC2626', selectedBg: '#FECACA' }, // Red
  { bg: '#FEF3C7', border: '#FDE68A', text: '#D97706', selectedBg: '#FDE68A' }, // Amber
  { bg: '#D1FAE5', border: '#A7F3D0', text: '#059669', selectedBg: '#A7F3D0' }, // Emerald
  { bg: '#DBEAFE', border: '#BFDBFE', text: '#2563EB', selectedBg: '#BFDBFE' }, // Blue
  { bg: '#E9D5FF', border: '#D8B4FE', text: '#9333EA', selectedBg: '#D8B4FE' }, // Purple
  { bg: '#FBCFE8', border: '#F9A8D4', text: '#DB2777', selectedBg: '#F9A8D4' }, // Pink
  { bg: '#CCFBF1', border: '#99F6E4', text: '#0D9488', selectedBg: '#99F6E4' }, // Teal
  { bg: '#FED7AA', border: '#FDBA74', text: '#EA580C', selectedBg: '#FDBA74' }, // Orange
] as const;

export type PillColor = typeof pillColors[number];

// Inspiration prompts - shown as tappable pills, randomized on mount
export const inspirationPrompts = [
  // Historical events
  { pill: "Napoleon's Return", prompt: "A true story about Napoleon escaping from Elba and marching back to Paris. Help kids understand the audacity and drama of this moment in history. Don't shy away from the political complexity but explain it in terms a 6yo can grasp." },
  { pill: 'French Revolution', prompt: "A story about the French Revolution and why the people rose up against their king. Include real historical details about the conditions that led to revolt. Use proper terms like 'monarchy' and 'revolution' but explain them for a 6yo." },
  { pill: 'Fall of Constantinople', prompt: "Tell the story of the last day of Constantinople in 1453. Help kids understand why this was such a significant moment in world history. Don't pull punches on the drama but use language a 6yo can understand." },
  { pill: 'Boston Tea Party', prompt: "A true story about the Boston Tea Party. Help kids understand why colonists felt so strongly about 'taxation without representation' that they dumped tea in the harbor. Explain the political concepts in terms a 6yo can grasp." },
  { pill: 'Moon Landing', prompt: "The true story of the Apollo 11 moon landing. Help kids understand both the technical achievement and the human courage involved. Use real terms like 'lunar module' and 'astronaut' but explain anything a 6yo wouldn't know." },
  { pill: 'Berlin Wall Falls', prompt: "A true story about the night the Berlin Wall fell and families were reunited. Help kids understand why the wall existed and what it meant when it came down. Don't shy away from the emotional weight but keep it appropriate for a 6yo." },
  { pill: 'Silk Road Journey', prompt: "A story about merchants traveling the ancient Silk Road between East and West. Include real details about what they traded and the dangers they faced. Help kids understand how this connected different civilizations." },
  // Human body & diseases
  { pill: 'How Arteries Clog', prompt: "Teach kids about atherosclerosis - how arteries get clogged over time. Don't shy away from real medical explanations. Use proper terms like 'plaque' and 'cholesterol' but explain anything a 6yo wouldn't be familiar with." },
  { pill: "Parkinson's Disease", prompt: "Help kids understand Parkinson's disease - why grandpa's hands might shake or why he moves differently. Use real medical terms like 'dopamine' and 'neurons' but explain them clearly for a 6yo. Don't shy away from the reality of the condition." },
  { pill: 'How Livers Work', prompt: "Teach kids how the liver works as the body's cleaning and processing factory. Include real biological details about filtering blood and producing bile. Use proper terms but explain anything a 6yo wouldn't know." },
  { pill: 'Fighting Cancer', prompt: "Help kids understand what cancer is and how the body fights it. Don't shy away from real explanations - use terms like 'cells', 'tumors', and 'immune system' but explain them for a 6yo. Be honest but age-appropriate about this serious topic." },
  { pill: 'Diabetes Explained', prompt: "Teach kids about diabetes - why some bodies need help managing sugar. Use real terms like 'insulin', 'pancreas', and 'blood sugar' but explain them clearly for a 6yo. Help them understand why someone might need to take medicine or watch what they eat." },
  { pill: 'How Vaccines Work', prompt: "Explain how vaccines train the immune system to fight diseases. Use real biological terms like 'antibodies', 'pathogens', and 'immune response' but explain them for a 6yo. Don't shy away from the science." },
  { pill: 'The Beating Heart', prompt: "Teach kids how the heart actually works - the chambers, valves, and electrical signals that keep it beating. Use proper anatomical terms but explain anything a 6yo wouldn't know. Include real facts about how many times it beats per day." },
  // Religious & philosophical
  { pill: "Arjuna's Dilemma", prompt: "Retell the scene from the Bhagavad Gita where Arjuna must fight against his own relatives. Focus on the concept of dharma (duty) but don't shy away from the moral difficulty - he still had to go to war against people he loved, and he felt terrible about it. Make it understandable to a 6yo." },
  { pill: 'Buddha Under Tree', prompt: "The true story of Prince Siddhartha who gave up everything to find enlightenment under the Bodhi tree. Help kids understand what he was searching for and what he discovered. Use terms like 'meditation' and 'enlightenment' but explain them for a 6yo." },
  { pill: 'David vs Goliath', prompt: "Tell the biblical story of David and Goliath. Help kids understand the courage it took for a young shepherd to face a giant warrior. Don't sanitize the battle but tell it in terms appropriate for a 6yo." },
  { pill: "Noah's Great Boat", prompt: "Tell the story of Noah building the ark. Help kids understand the scale of what he was asked to do and why people thought he was crazy. Include real details about the size of the ark and the animals. Keep it understandable for a 6yo." },
  { pill: 'The Good Samaritan', prompt: "Tell Jesus's parable of the Good Samaritan. Help kids understand why it was so surprising that the Samaritan helped when others didn't - explain the historical context of who Samaritans were. Make the moral lesson clear for a 6yo." },
  { pill: "Muhammad's Journey", prompt: "Tell the story of the Prophet Muhammad's night journey (Isra and Mi'raj) to the heavens. Help kids understand why this is such an important story in Islam. Use respectful language and explain any terms a 6yo wouldn't know." },
  // Science & nature
  { pill: 'How Stars Die', prompt: "Teach kids about how stars die - from red giants to supernovae to black holes. Don't shy away from the real astrophysics. Use terms like 'nuclear fusion', 'supernova', and 'neutron star' but explain them for a 6yo." },
  { pill: 'Dinosaur Extinction', prompt: "Tell the true story of how the dinosaurs went extinct. Include real scientific details about the asteroid impact, the 'nuclear winter' effect, and why some animals survived. Use proper terms but explain them for a 6yo." },
  { pill: 'How Bees Dance', prompt: "Teach kids about the waggle dance - how bees communicate the location of flowers to each other. Include real scientific details about angles and distances. Help kids understand how remarkable this communication system is." },
  { pill: 'Volcano Erupts', prompt: "Explain what really happens when a volcano erupts - magma chambers, tectonic plates, and pyroclastic flows. Use proper geological terms but explain anything a 6yo wouldn't know. Don't shy away from the destructive power." },
  { pill: 'Ice Age Begins', prompt: "Explain how ice ages happen - Milankovitch cycles, ocean currents, and feedback loops. Help kids understand the science behind why Earth's climate changes over long periods. Use real terms but explain them for a 6yo." },
  // Philosophy & ideas
  { pill: 'Socrates Questions', prompt: "Tell the story of Socrates - the philosopher who kept asking questions until it made powerful people angry enough to execute him. Help kids understand the Socratic method and why asking 'why' matters. Don't shy away from how the story ends." },
  { pill: "Plato's Cave", prompt: "Explain Plato's allegory of the cave - prisoners who only saw shadows and what happened when one escaped to see reality. Help kids understand what Plato was trying to teach about knowledge and perception. Make this philosophy accessible to a 6yo." },
  { pill: 'Golden Rule', prompt: "Explore how the Golden Rule ('treat others as you want to be treated') appears across different cultures and religions around the world. Help kids understand why this idea keeps showing up everywhere. Include real examples from different traditions." },
] as const;

export type InspirationPrompt = typeof inspirationPrompts[number];
