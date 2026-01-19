"""
Validated test cases for homograph disambiguation.

Each homograph has exactly 5 sentences per pronunciation (index 0 and index 1).
Total: 47 homographs × 2 pronunciations × 5 sentences = 470 test cases.

Format: (sentence, word, expected_index)
- index 0: first pronunciation in homographs.ts
- index 1: second pronunciation in homographs.ts
"""

# =============================================================================
# VOWEL/CONSONANT CHANGE HOMOGRAPHS (18 words)
# =============================================================================

READ_CASES = [
    # Index 0: /riːd/ pronunciation
    ("I read books every morning before work.", "read", 0),
    ("Can you read this sign from here?", "read", 0),
    ("Children learn to read in first grade.", "read", 0),
    ("She loves to read mystery novels.", "read", 0),
    ("Please read the instructions carefully.", "read", 0),
    # Index 1: past tense /rɛd/ - "I read it yesterday"
    ("She read the entire novel last night.", "read", 1),
    ("I read that article yesterday.", "read", 1),
    ("He had already read the memo before the meeting.", "read", 1),
    ("They read all the documents last week.", "read", 1),
    ("The teacher read the story to the class yesterday.", "read", 1),
]

LEAD_CASES = [
    # Index 0: verb /liːd/ - "to lead the way"
    ("She will lead the expedition through the jungle.", "lead", 0),
    ("Who will lead the meeting today?", "lead", 0),
    ("The captain must lead by example.", "lead", 0),
    ("Can you lead me to the exit?", "lead", 0),
    ("Great coaches lead their teams to victory.", "lead", 0),
    # Index 1: noun (metal) /lɛd/ - "the metal lead"
    ("The pipes are made of lead.", "lead", 1),
    ("Lead poisoning is dangerous for children.", "lead", 1),
    ("The pencil contains graphite, not lead.", "lead", 1),
    ("Workers removed the lead paint from the walls.", "lead", 1),
    ("The fishing line has a lead weight attached.", "lead", 1),
]

LIVE_CASES = [
    # Index 0: verb /lɪv/ - "I live here"
    ("I live in a small apartment downtown.", "live", 0),
    ("Where do you live?", "live", 0),
    ("They live near the beach.", "live", 0),
    ("We live in interesting times.", "live", 0),
    ("Fish cannot live outside of water.", "live", 0),
    # Index 1: adjective /laɪv/ - "live music"
    ("The band is performing live tonight.", "live", 1),
    ("We watched the live broadcast of the game.", "live", 1),
    ("The show features live animals.", "live", 1),
    ("Be careful, those are live wires.", "live", 1),
    ("The restaurant has live music on weekends.", "live", 1),
]

WIND_CASES = [
    # Index 0: noun /wɪnd/ - "the wind blows"
    ("The wind is blowing hard today.", "wind", 0),
    ("A cold wind swept through the valley.", "wind", 0),
    ("The wind knocked down several trees.", "wind", 0),
    ("Sailors rely on the wind to move their boats.", "wind", 0),
    ("The wind carried the leaves across the yard.", "wind", 0),
    # Index 1: verb /waɪnd/ - "wind the clock"
    ("Please wind the clock before bed.", "wind", 1),
    ("You need to wind the music box to play it.", "wind", 1),
    ("Wind the thread around the spool carefully.", "wind", 1),
    ("The road will wind through the mountains.", "wind", 1),
    ("She had to wind the yarn into a ball.", "wind", 1),
]

WOUND_CASES = [
    # Index 0: noun /wuːnd/ - "a wound on his arm"
    ("The wound on his arm needed stitches.", "wound", 0),
    ("She cleaned the wound with antiseptic.", "wound", 0),
    ("The soldier received a wound in battle.", "wound", 0),
    ("The wound healed quickly without infection.", "wound", 0),
    ("Apply pressure to stop the wound from bleeding.", "wound", 0),
    # Index 1: past tense of wind /waʊnd/ - "wound the string"
    ("She wound the string around her finger.", "wound", 1),
    ("He wound the clock every night before bed.", "wound", 1),
    ("The path wound through the dense forest.", "wound", 1),
    ("They wound the bandage tightly around the injury.", "wound", 1),
    ("The river wound its way to the sea.", "wound", 1),
]

TEAR_CASES = [
    # Index 0: noun /tɪr/ - "a tear from her eye"
    ("A tear rolled down her cheek.", "tear", 0),
    ("He wiped the tear from his eye.", "tear", 0),
    ("The sad movie brought a tear to my eye.", "tear", 0),
    ("Not a single tear was shed at the farewell.", "tear", 0),
    ("She tried to hide the tear in her eye.", "tear", 0),
    # Index 1: verb /tɛr/ - "tear the paper"
    ("Be careful not to tear the wrapping paper.", "tear", 1),
    ("The dog will tear the toy apart.", "tear", 1),
    ("Please tear along the dotted line.", "tear", 1),
    ("The thorns will tear your clothes.", "tear", 1),
    ("Do not tear the pages out of the book.", "tear", 1),
]

BOW_CASES = [
    # Index 0: noun /boʊ/ - "a bow and arrow"
    ("She tied a red bow in her hair.", "bow", 0),
    ("He drew his bow and aimed at the target.", "bow", 0),
    ("The gift had a beautiful bow on top.", "bow", 0),
    ("The archer carried a wooden bow.", "bow", 0),
    ("Robin Hood was famous for his bow and arrow.", "bow", 0),
    # Index 1: verb /baʊ/ - "bow to the queen"
    ("The performers bow to the audience after the show.", "bow", 1),
    ("You must bow before the king.", "bow", 1),
    ("The actors will bow when the curtain falls.", "bow", 1),
    ("In Japan, people bow as a greeting.", "bow", 1),
    ("The knight had to bow to the queen.", "bow", 1),
]

ROW_CASES = [
    # Index 0: noun /roʊ/ - "a row of seats"
    ("We sat in the front row at the theater.", "row", 0),
    ("Plant the seeds in a straight row.", "row", 0),
    ("There was a row of houses along the street.", "row", 0),
    ("She arranged the books in a neat row.", "row", 0),
    ("The students stood in a row for the photo.", "row", 0),
    # Index 1: noun (argument) /raʊ/ - "a heated argument" (British English)
    ("They had a terrible row, shouting and slamming doors.", "row", 1),
    ("The neighbors got into a heated row over the fence.", "row", 1),
    ("A furious row broke out between the two families.", "row", 1),
    ("The couple had a blazing row that woke the neighbors.", "row", 1),
    ("There was an almighty row when he came home late.", "row", 1),
]

SOW_CASES = [
    # Index 0: verb /soʊ/ - "sow the seeds"
    ("Farmers sow seeds in the spring.", "sow", 0),
    ("You reap what you sow.", "sow", 0),
    ("It is time to sow the wheat.", "sow", 0),
    ("They will sow the field with corn.", "sow", 0),
    ("We should sow the garden before the rain.", "sow", 0),
    # Index 1: noun /saʊ/ - "a female pig"
    ("The sow gave birth to eight piglets.", "sow", 1),
    ("The farmer fed the sow in the barn.", "sow", 1),
    ("A sow can weigh over 300 pounds.", "sow", 1),
    ("The sow protected her piglets fiercely.", "sow", 1),
    ("They bought a sow at the livestock auction.", "sow", 1),
]

BASS_CASES = [
    # Index 0: noun /beɪs/ - "bass guitar"
    ("He plays bass in the band.", "bass", 0),
    ("The bass guitar provides the low notes.", "bass", 0),
    ("Turn up the bass on the stereo.", "bass", 0),
    ("She has a deep bass voice.", "bass", 0),
    ("The bass line in this song is amazing.", "bass", 0),
    # Index 1: noun /bæs/ - "bass fish"
    ("We caught a large bass at the lake.", "bass", 1),
    ("Bass are common in freshwater lakes.", "bass", 1),
    ("The bass weighed nearly ten pounds.", "bass", 1),
    ("Grilled bass is delicious with lemon.", "bass", 1),
    ("He went fishing for bass this morning.", "bass", 1),
]

CLOSE_CASES = [
    # Index 0: verb /kloʊz/ - "close the door"
    ("Please close the door behind you.", "close", 0),
    ("The store will close at nine tonight.", "close", 0),
    ("Remember to close your eyes during the surprise.", "close", 0),
    ("She forgot to close the window.", "close", 0),
    ("They decided to close the deal today.", "close", 0),
    # Index 1: adjective /kloʊs/ - "close to home"
    ("The hotel is close to the beach.", "close", 1),
    ("We are very close friends.", "close", 1),
    ("The election was extremely close.", "close", 1),
    ("Keep a close watch on the children.", "close", 1),
    ("She lives close to her parents.", "close", 1),
]

USE_CASES = [
    # Index 0: verb /juːz/ - "use the tool"
    ("You can use my phone if you need to.", "use", 0),
    ("Please use the stairs in case of fire.", "use", 0),
    ("Learn how to use the software properly.", "use", 0),
    ("May I use your bathroom?", "use", 0),
    ("They use solar panels for electricity.", "use", 0),
    # Index 1: noun /juːs/ - "no use trying"
    ("There is no use crying over spilled milk.", "use", 1),
    ("What is the use of complaining?", "use", 1),
    ("This tool has many practical uses.", "use", 1),
    ("The use of phones is prohibited during the exam.", "use", 1),
    ("She found a new use for the old container.", "use", 1),
]

HOUSE_CASES = [
    # Index 0: noun /haʊs/ - "the house"
    ("The house on the corner is for sale.", "house", 0),
    ("They bought a new house last year.", "house", 0),
    ("The house has three bedrooms.", "house", 0),
    ("Our house needs a new roof.", "house", 0),
    ("The old house was built in 1920.", "house", 0),
    # Index 1: verb /haʊz/ - "house the refugees"
    ("The shelter can house fifty families.", "house", 1),
    ("This building will house the new museum.", "house", 1),
    ("The barn was used to house the animals.", "house", 1),
    ("They needed a bigger facility to house all the equipment.", "house", 1),
    ("The dormitory will house students from overseas.", "house", 1),
]

EXCUSE_CASES = [
    # Index 0: verb /ɪkˈskjuːz/ - "excuse me"
    ("Excuse me, could you help me find the exit?", "excuse", 0),
    ("Please excuse my late arrival.", "excuse", 0),
    ("I hope you can excuse the mess.", "excuse", 0),
    ("Excuse me for interrupting.", "excuse", 0),
    ("We cannot excuse such behavior.", "excuse", 0),
    # Index 1: noun /ɪkˈskjuːs/ - "a poor excuse"
    ("That is a poor excuse for being late.", "excuse", 1),
    ("He always has an excuse ready.", "excuse", 1),
    ("There is no excuse for rudeness.", "excuse", 1),
    ("She made up an excuse to leave early.", "excuse", 1),
    ("His excuse did not convince anyone.", "excuse", 1),
]

DOVE_CASES = [
    # Index 0: noun /dʌv/ - "a white dove"
    ("A white dove landed on the windowsill.", "dove", 0),
    ("The dove is a symbol of peace.", "dove", 0),
    ("They released a dove at the ceremony.", "dove", 0),
    ("The dove cooed softly in the tree.", "dove", 0),
    ("A dove built a nest on our balcony.", "dove", 0),
    # Index 1: past tense of dive /doʊv/ - "she dove into the pool"
    ("She dove into the pool headfirst.", "dove", 1),
    ("The goalkeeper dove to save the ball.", "dove", 1),
    ("He dove under the table when he heard the noise.", "dove", 1),
    ("The bird dove down to catch the fish.", "dove", 1),
    ("She dove off the high board gracefully.", "dove", 1),
]

DOES_CASES = [
    # Index 0: verb /dʌz/ - "she does it"
    ("She does her homework every evening.", "does", 0),
    ("He does not understand the question.", "does", 0),
    ("What does this word mean?", "does", 0),
    ("It does not matter anymore.", "does", 0),
    ("Nobody does it better than her.", "does", 0),
    # Index 1: noun /doʊz/ - "female deer"
    ("The does grazed peacefully in the meadow.", "does", 1),
    ("Several does and their fawns crossed the road.", "does", 1),
    ("The hunter spotted three does near the stream.", "does", 1),
    ("Female deer, called does, are typically smaller than bucks.", "does", 1),
    ("We counted five does and two bucks in the field.", "does", 1),
]

SEWER_CASES = [
    # Index 0: noun /ˈsuːər/ - "the sewer pipe"
    ("The sewer pipe was clogged with debris.", "sewer", 0),
    ("Rats live in the city sewer.", "sewer", 0),
    ("The sewer system needs major repairs.", "sewer", 0),
    ("A bad smell came from the sewer.", "sewer", 0),
    ("They climbed down into the sewer to escape.", "sewer", 0),
    # Index 1: noun /ˈsoʊər/ - "one who sews"
    ("The sewer finished the dress in two days.", "sewer", 1),
    ("She is an expert sewer and makes all her own clothes.", "sewer", 1),
    ("The sewer repaired the torn seam perfectly.", "sewer", 1),
    ("As a professional sewer, she works at a tailor shop.", "sewer", 1),
    ("The sewer carefully stitched the delicate fabric.", "sewer", 1),
]

POLISH_CASES = [
    # Index 0: verb /ˈpɑlɪʃ/ - "polish the shoes"
    ("Please polish your shoes before the interview.", "polish", 0),
    ("She used wax to polish the wooden floor.", "polish", 0),
    ("I need to polish the silverware for dinner.", "polish", 0),
    ("He forgot to polish his presentation.", "polish", 0),
    ("The butler will polish the brass handles.", "polish", 0),
    # Index 1: adjective /ˈpoʊlɪʃ/ - "Polish language"
    ("She speaks fluent Polish.", "polish", 1),
    ("The Polish festival features traditional dances.", "polish", 1),
    ("He is learning Polish to talk to his grandmother.", "polish", 1),
    ("Polish cuisine includes delicious pierogies.", "polish", 1),
    ("The Polish flag is white and red.", "polish", 1),
]

# =============================================================================
# STRESS-SHIFT HOMOGRAPHS (29 words)
# =============================================================================

PRESENT_CASES = [
    # Index 0: noun /ˈprɛzənt/ - "a birthday present"
    ("She gave me a birthday present.", "present", 0),
    ("The present was wrapped in blue paper.", "present", 0),
    ("What a lovely present you bought!", "present", 0),
    ("He forgot to bring a present to the party.", "present", 0),
    ("The children opened their presents on Christmas morning.", "present", 0),
    # Index 1: verb /prɪˈzɛnt/ - "present the award"
    ("I will present my findings at the conference.", "present", 1),
    ("The mayor will present the award tonight.", "present", 1),
    ("Let me present the new product to you.", "present", 1),
    ("She was asked to present the proposal to the board.", "present", 1),
    ("They will present evidence in court tomorrow.", "present", 1),
]

RECORD_CASES = [
    # Index 0: noun /ˈrɛkərd/ - "a vinyl record"
    ("I bought a vintage record at the shop.", "record", 0),
    ("The record skipped during the song.", "record", 0),
    ("She broke the world record in swimming.", "record", 0),
    ("This is my favorite record of all time.", "record", 0),
    ("The record sold over a million copies.", "record", 0),
    # Index 1: verb /rɪˈkɔrd/ - "record a song"
    ("They will record the album next month.", "record", 1),
    ("Please record this meeting for those who are absent.", "record", 1),
    ("I forgot to record my favorite show.", "record", 1),
    ("The band wants to record a new single.", "record", 1),
    ("Make sure to record your expenses carefully.", "record", 1),
]

PRODUCE_CASES = [
    # Index 0: noun /ˈprɑduːs/ - "fresh produce"
    ("The produce at the farmers market is very fresh.", "produce", 0),
    ("We buy organic produce whenever possible.", "produce", 0),
    ("The store has a great selection of produce.", "produce", 0),
    ("Fresh produce is essential for a healthy diet.", "produce", 0),
    ("The produce section is at the back of the store.", "produce", 0),
    # Index 1: verb /prəˈduːs/ - "produce results"
    ("This factory can produce a thousand units per day.", "produce", 1),
    ("We need to produce better results this quarter.", "produce", 1),
    ("Artists produce their best work under pressure.", "produce", 1),
    ("The new policy will produce significant savings.", "produce", 1),
    ("Can you produce evidence to support your claim?", "produce", 1),
]

OBJECT_CASES = [
    # Index 0: noun /ˈɑbdʒɛkt/ - "a shiny object"
    ("A strange object fell from the sky.", "object", 0),
    ("The object on the table caught my attention.", "object", 0),
    ("What is that shiny object in the corner?", "object", 0),
    ("The object of the game is to score points.", "object", 0),
    ("She picked up an unusual object from the beach.", "object", 0),
    # Index 1: verb /əbˈdʒɛkt/ - "I object!"
    ("I object to this line of questioning.", "object", 1),
    ("Does anyone object to the proposal?", "object", 1),
    ("The lawyer will object if you ask that question.", "object", 1),
    ("Many citizens object to the new tax.", "object", 1),
    ("I strongly object to being treated this way.", "object", 1),
]

CONTENT_CASES = [
    # Index 0: noun /ˈkɑntɛnt/ - "the content of the book"
    ("The content of the article was controversial.", "content", 0),
    ("Please review the content before publishing.", "content", 0),
    ("The website lacks quality content.", "content", 0),
    ("The content of her speech was inspiring.", "content", 0),
    ("We need to update the content on our homepage.", "content", 0),
    # Index 1: adjective /kənˈtɛnt/ - "feeling content"
    ("She felt content with her simple life.", "content", 1),
    ("The cat looked content sleeping in the sun.", "content", 1),
    ("He was finally content after years of struggle.", "content", 1),
    ("They seemed perfectly content with the arrangement.", "content", 1),
    ("I am content to stay home this evening.", "content", 1),
]

CONTRACT_CASES = [
    # Index 0: noun /ˈkɑntrækt/ - "sign the contract"
    ("Please sign the contract by Friday.", "contract", 0),
    ("The contract expires next month.", "contract", 0),
    ("They negotiated a new contract with the supplier.", "contract", 0),
    ("Read the contract carefully before signing.", "contract", 0),
    ("The contract includes a confidentiality clause.", "contract", 0),
    # Index 1: verb /kənˈtrækt/ - "muscles contract"
    ("Cold causes metal to contract.", "contract", 1),
    ("Your muscles contract when you exercise.", "contract", 1),
    ("The pupils contract in bright light.", "contract", 1),
    ("Materials expand and contract with temperature changes.", "contract", 1),
    ("The heart muscles contract to pump blood.", "contract", 1),
]

REFUSE_CASES = [
    # Index 0: noun /ˈrɛfjuːs/ - "refuse/garbage"
    ("The refuse was collected on Tuesday.", "refuse", 0),
    ("Please dispose of refuse in the proper bins.", "refuse", 0),
    ("The refuse pile attracted rats.", "refuse", 0),
    ("Industrial refuse polluted the river.", "refuse", 0),
    ("The city improved its refuse collection service.", "refuse", 0),
    # Index 1: verb /rɪˈfjuːz/ - "refuse to go"
    ("I refuse to accept these conditions.", "refuse", 1),
    ("She will refuse any offer below that amount.", "refuse", 1),
    ("You cannot refuse a direct order.", "refuse", 1),
    ("They refuse to negotiate with terrorists.", "refuse", 1),
    ("He may refuse to testify in court.", "refuse", 1),
]

DESERT_CASES = [
    # Index 0: noun /ˈdɛzərt/ - "the Sahara desert"
    ("The Sahara is the largest hot desert in the world.", "desert", 0),
    ("Camels are well adapted to the desert.", "desert", 0),
    ("The desert gets very cold at night.", "desert", 0),
    ("They drove across the desert for hours.", "desert", 0),
    ("Few plants can survive in the desert.", "desert", 0),
    # Index 1: verb /dɪˈzɜrt/ - "desert the army"
    ("Soldiers who desert face serious consequences.", "desert", 1),
    ("He decided to desert his post during the battle.", "desert", 1),
    ("Many rats desert a sinking ship.", "desert", 1),
    ("She would never desert her friends in need.", "desert", 1),
    ("The coward chose to desert when danger came.", "desert", 1),
]

MINUTE_CASES = [
    # Index 0: noun /ˈmɪnɪt/ - "one minute"
    ("Wait just one minute please.", "minute", 0),
    ("The meeting lasted sixty minutes.", "minute", 0),
    ("I will be there in a minute.", "minute", 0),
    ("The minute hand on the clock is broken.", "minute", 0),
    ("She finished the race in under four minutes.", "minute", 0),
    # Index 1: adjective /maɪˈnjuːt/ - "minute details"
    ("The detective noticed minute details at the scene.", "minute", 1),
    ("There were minute differences between the two samples.", "minute", 1),
    ("She examined the painting in minute detail.", "minute", 1),
    ("The changes were so minute they were barely noticeable.", "minute", 1),
    ("Scientists study minute organisms under microscopes.", "minute", 1),
]

SEPARATE_CASES = [
    # Index 0: adjective /ˈsɛpərɪt/ - "separate rooms"
    ("They sleep in separate bedrooms.", "separate", 0),
    ("Please use a separate sheet for each answer.", "separate", 0),
    ("The twins have very separate personalities.", "separate", 0),
    ("We need separate accounts for business and personal.", "separate", 0),
    ("They went their separate ways after graduation.", "separate", 0),
    # Index 1: verb /ˈsɛpəreɪt/ - "separate the items"
    ("Please separate the whites from the colors.", "separate", 1),
    ("We need to separate the recyclables from the trash.", "separate", 1),
    ("The teacher had to separate the fighting students.", "separate", 1),
    ("Oil and water naturally separate.", "separate", 1),
    ("It is hard to separate fact from fiction.", "separate", 1),
]

ALTERNATE_CASES = [
    # Index 0: adjective/noun /ˈɔltərnɪt/ - "an alternate route"
    ("Take the alternate route to avoid traffic.", "alternate", 0),
    ("She is the alternate delegate for the conference.", "alternate", 0),
    ("We need an alternate plan in case this fails.", "alternate", 0),
    ("The alternate entrance is around the back.", "alternate", 0),
    ("He served as an alternate on the jury.", "alternate", 0),
    # Index 1: verb /ˈɔltərneɪt/ - "alternate between"
    ("The weather tends to alternate between sun and rain.", "alternate", 1),
    ("They alternate shifts at the factory.", "alternate", 1),
    ("You should alternate between different exercises.", "alternate", 1),
    ("The lights alternate between red and green.", "alternate", 1),
    ("We alternate hosting duties each month.", "alternate", 1),
]

ATTRIBUTE_CASES = [
    # Index 0: noun /ˈætrɪbjuːt/ - "a key attribute"
    ("Patience is an important attribute for teachers.", "attribute", 0),
    ("Honesty is her best attribute.", "attribute", 0),
    ("Each product has a unique attribute.", "attribute", 0),
    ("Leadership is a valuable attribute in managers.", "attribute", 0),
    ("The attribute of kindness is often undervalued.", "attribute", 0),
    # Index 1: verb /əˈtrɪbjuːt/ - "attribute to luck"
    ("Many attribute her success to hard work.", "attribute", 1),
    ("Historians attribute the quote to Lincoln.", "attribute", 1),
    ("Do not attribute motives to others unfairly.", "attribute", 1),
    ("Scientists attribute climate change to human activity.", "attribute", 1),
    ("Some attribute the painting to Rembrandt.", "attribute", 1),
]

ENTRANCE_CASES = [
    # Index 0: noun /ˈɛntrəns/ - "the main entrance"
    ("The main entrance is on the north side.", "entrance", 0),
    ("Please use the side entrance.", "entrance", 0),
    ("The entrance to the cave was hidden by vines.", "entrance", 0),
    ("There is a long queue at the entrance.", "entrance", 0),
    ("The entrance fee is ten dollars.", "entrance", 0),
    # Index 1: verb /ɪnˈtræns/ - "entrance the audience"
    ("The magician will entrance the audience with his tricks.", "entrance", 1),
    ("Her beauty seemed to entrance everyone in the room.", "entrance", 1),
    ("The storyteller could entrance children for hours.", "entrance", 1),
    ("The hypnotist tried to entrance the volunteer.", "entrance", 1),
    ("His music has the power to entrance listeners.", "entrance", 1),
]

GRADUATE_CASES = [
    # Index 0: noun /ˈɡrædʒuɪt/ - "a college graduate"
    ("She is a graduate of Harvard University.", "graduate", 0),
    ("The graduate received her diploma on stage.", "graduate", 0),
    ("As a recent graduate, he is looking for work.", "graduate", 0),
    ("The proud graduate posed for photographs.", "graduate", 0),
    ("Every graduate should attend the ceremony.", "graduate", 0),
    # Index 1: verb /ˈɡrædʒueɪt/ - "graduate from school"
    ("She will graduate from college next spring.", "graduate", 1),
    ("He hopes to graduate with honors.", "graduate", 1),
    ("Students who graduate must complete all requirements.", "graduate", 1),
    ("When did you graduate from high school?", "graduate", 1),
    ("They plan to graduate together next year.", "graduate", 1),
]

BUFFET_CASES = [
    # Index 0: noun /bəˈfeɪ/ - "a breakfast buffet"
    ("The hotel offers a delicious breakfast buffet.", "buffet", 0),
    ("We chose the buffet option for the reception.", "buffet", 0),
    ("The buffet included a variety of seafood.", "buffet", 0),
    ("There is an all-you-can-eat buffet on Sundays.", "buffet", 0),
    ("The buffet table was beautifully arranged.", "buffet", 0),
    # Index 1: verb /ˈbʌfɪt/ - "winds buffet the coast"
    ("Strong winds buffet the coastal towns.", "buffet", 1),
    ("Waves buffet the small fishing boat.", "buffet", 1),
    ("The economy continues to buffet small businesses.", "buffet", 1),
    ("Storms buffet the island every hurricane season.", "buffet", 1),
    ("Critics buffet the politician from all sides.", "buffet", 1),
]

PERMIT_CASES = [
    # Index 0: noun /ˈpɜrmɪt/ - "a parking permit"
    ("You need a permit to park here.", "permit", 0),
    ("The building permit was approved yesterday.", "permit", 0),
    ("She applied for a work permit.", "permit", 0),
    ("Fishing without a permit is illegal.", "permit", 0),
    ("The permit expires at the end of the month.", "permit", 0),
    # Index 1: verb /pərˈmɪt/ - "permit entry"
    ("They do not permit smoking indoors.", "permit", 1),
    ("Will you permit me to explain?", "permit", 1),
    ("The rules permit only two guests per member.", "permit", 1),
    ("Weather permitting, we will have the picnic outside.", "permit", 1),
    ("The law does not permit such behavior.", "permit", 1),
]

CONDUCT_CASES = [
    # Index 0: noun /ˈkɑndʌkt/ - "good conduct"
    ("His conduct at the meeting was unprofessional.", "conduct", 0),
    ("The student was praised for excellent conduct.", "conduct", 0),
    ("A code of conduct applies to all employees.", "conduct", 0),
    ("Her conduct during the crisis was admirable.", "conduct", 0),
    ("The soldier received a medal for good conduct.", "conduct", 0),
    # Index 1: verb /kənˈdʌkt/ - "conduct the orchestra"
    ("She will conduct the orchestra tonight.", "conduct", 1),
    ("They plan to conduct a survey next week.", "conduct", 1),
    ("The scientist will conduct experiments in the lab.", "conduct", 1),
    ("Metal wires conduct electricity.", "conduct", 1),
    ("He was hired to conduct the investigation.", "conduct", 1),
]

CONFLICT_CASES = [
    # Index 0: noun /ˈkɑnflɪkt/ - "a conflict arose"
    ("A conflict arose between the two departments.", "conflict", 0),
    ("The conflict lasted for several years.", "conflict", 0),
    ("There is a conflict of interest in this case.", "conflict", 0),
    ("The movie is about an armed conflict.", "conflict", 0),
    ("They resolved the conflict peacefully.", "conflict", 0),
    # Index 1: verb /kənˈflɪkt/ - "schedules conflict"
    ("Our schedules conflict on Tuesdays.", "conflict", 1),
    ("These two reports conflict with each other.", "conflict", 1),
    ("His testimony may conflict with the evidence.", "conflict", 1),
    ("The new policy will conflict with existing rules.", "conflict", 1),
    ("Their accounts of the incident conflict.", "conflict", 1),
]

CONTEST_CASES = [
    # Index 0: noun /ˈkɑntɛst/ - "a singing contest"
    ("She won first place in the contest.", "contest", 0),
    ("The contest attracted hundreds of participants.", "contest", 0),
    ("Entry to the contest is free.", "contest", 0),
    ("The beauty contest will be held on Saturday.", "contest", 0),
    ("He entered a baking contest.", "contest", 0),
    # Index 1: verb /kənˈtɛst/ - "contest the decision"
    ("They plan to contest the election results.", "contest", 1),
    ("The lawyer will contest the will.", "contest", 1),
    ("Several teams will contest the championship.", "contest", 1),
    ("She decided to contest the parking ticket.", "contest", 1),
    ("Athletes from many countries will contest the title.", "contest", 1),
]

CONVERT_CASES = [
    # Index 0: noun /ˈkɑnvɜrt/ - "a religious convert"
    ("He is a recent convert to Buddhism.", "convert", 0),
    ("The convert was welcomed into the congregation.", "convert", 0),
    ("As a convert, she takes her new faith seriously.", "convert", 0),
    ("The convert shared his story with the group.", "convert", 0),
    ("She became a convert after studying the teachings.", "convert", 0),
    # Index 1: verb /kənˈvɜrt/ - "convert to metric"
    ("We need to convert the measurements to metric.", "convert", 1),
    ("The app can convert currencies instantly.", "convert", 1),
    ("They want to convert the garage into a bedroom.", "convert", 1),
    ("How do you convert Fahrenheit to Celsius?", "convert", 1),
    ("The company plans to convert to renewable energy.", "convert", 1),
]

CONVICT_CASES = [
    # Index 0: noun /ˈkɑnvɪkt/ - "an escaped convict"
    ("The convict escaped from prison last night.", "convict", 0),
    ("A convict was spotted near the highway.", "convict", 0),
    ("The convict served ten years for robbery.", "convict", 0),
    ("Former convicts often struggle to find employment.", "convict", 0),
    ("The convict pleaded for an early release.", "convict", 0),
    # Index 1: verb /kənˈvɪkt/ - "convict the defendant"
    ("The jury voted to convict the defendant.", "convict", 1),
    ("There was not enough evidence to convict.", "convict", 1),
    ("They failed to convict him of the crime.", "convict", 1),
    ("The prosecution aims to convict the accused.", "convict", 1),
    ("It is difficult to convict without witnesses.", "convict", 1),
]

INSERT_CASES = [
    # Index 0: noun /ˈɪnsɜrt/ - "a magazine insert"
    ("The magazine came with a special insert.", "insert", 0),
    ("The insert contains coupons for local stores.", "insert", 0),
    ("Please read the insert before taking the medication.", "insert", 0),
    ("The newspaper had a colorful advertising insert.", "insert", 0),
    ("The DVD includes a booklet insert.", "insert", 0),
    # Index 1: verb /ɪnˈsɜrt/ - "insert the key"
    ("Insert your card into the machine.", "insert", 1),
    ("Please insert the key and turn it clockwise.", "insert", 1),
    ("You need to insert a coin to start.", "insert", 1),
    ("Insert the USB drive into the port.", "insert", 1),
    ("The surgeon will insert a small camera.", "insert", 1),
]

INVALID_CASES = [
    # Index 0: noun /ˈɪnvəlɪd/ - "care for an invalid"
    ("She spent years caring for an invalid relative.", "invalid", 0),
    ("The invalid required round-the-clock assistance.", "invalid", 0),
    ("He became an invalid after the accident.", "invalid", 0),
    ("The home was designed for invalids.", "invalid", 0),
    ("The invalid was confined to a wheelchair.", "invalid", 0),
    # Index 1: adjective /ɪnˈvælɪd/ - "an invalid password"
    ("Your password is invalid.", "invalid", 1),
    ("The ticket was declared invalid.", "invalid", 1),
    ("The contract is invalid without a signature.", "invalid", 1),
    ("That is an invalid argument.", "invalid", 1),
    ("The visa became invalid after it expired.", "invalid", 1),
]

PROJECT_CASES = [
    # Index 0: noun /ˈprɑdʒɛkt/ - "a school project"
    ("The science project is due on Monday.", "project", 0),
    ("She is working on a big project at work.", "project", 0),
    ("The construction project will take two years.", "project", 0),
    ("Our team completed the project on time.", "project", 0),
    ("The project requires a lot of research.", "project", 0),
    # Index 1: verb /prəˈdʒɛkt/ - "project an image"
    ("The device can project images onto any surface.", "project", 1),
    ("Analysts project growth of five percent.", "project", 1),
    ("Try not to project your feelings onto others.", "project", 1),
    ("The lighthouse can project light for miles.", "project", 1),
    ("Experts project the population will double.", "project", 1),
]

REBEL_CASES = [
    # Index 0: noun /ˈrɛbəl/ - "a rebel fighter"
    ("The rebel led an uprising against the government.", "rebel", 0),
    ("She was always a rebel in school.", "rebel", 0),
    ("The rebel forces captured the capital.", "rebel", 0),
    ("He joined the rebels in the mountains.", "rebel", 0),
    ("The rebel refused to follow orders.", "rebel", 0),
    # Index 1: verb /rɪˈbɛl/ - "rebel against authority"
    ("Teenagers often rebel against their parents.", "rebel", 1),
    ("The citizens decided to rebel against the tyrant.", "rebel", 1),
    ("Workers may rebel if conditions do not improve.", "rebel", 1),
    ("She started to rebel against strict rules.", "rebel", 1),
    ("The provinces threatened to rebel against the empire.", "rebel", 1),
]

SUBJECT_CASES = [
    # Index 0: noun /ˈsʌbdʒɪkt/ - "the subject of the book"
    ("Math is my favorite subject.", "subject", 0),
    ("The subject of the painting is a young woman.", "subject", 0),
    ("Let us change the subject.", "subject", 0),
    ("The email subject should be clear.", "subject", 0),
    ("History was her best subject in school.", "subject", 0),
    # Index 1: verb /səbˈdʒɛkt/ - "subject to questioning"
    ("They will subject the theory to rigorous testing.", "subject", 1),
    ("Do not subject yourself to unnecessary stress.", "subject", 1),
    ("The new policy will subject everyone to review.", "subject", 1),
    ("They plan to subject the data to analysis.", "subject", 1),
    ("The officers will subject him to intense questioning.", "subject", 1),
]

SUSPECT_CASES = [
    # Index 0: noun /ˈsʌspɛkt/ - "a prime suspect"
    ("The police arrested the main suspect.", "suspect", 0),
    ("He became a suspect in the investigation.", "suspect", 0),
    ("The suspect was seen leaving the building.", "suspect", 0),
    ("She is no longer a suspect in the case.", "suspect", 0),
    ("The suspect denied all allegations.", "suspect", 0),
    # Index 1: verb /səˈspɛkt/ - "I suspect fraud"
    ("I suspect he is lying.", "suspect", 1),
    ("Police suspect foul play in his death.", "suspect", 1),
    ("We suspect the system has a bug.", "suspect", 1),
    ("I suspect she already knows the answer.", "suspect", 1),
    ("Doctors suspect an allergic reaction.", "suspect", 1),
]

CONSOLE_CASES = [
    # Index 0: noun /ˈkɑnsoʊl/ - "a game console"
    ("He bought a new game console.", "console", 0),
    ("The console is connected to the television.", "console", 0),
    ("The console table is in the hallway.", "console", 0),
    ("She plays games on her console every day.", "console", 0),
    ("The latest console has amazing graphics.", "console", 0),
    # Index 1: verb /kənˈsoʊl/ - "console the grieving"
    ("She tried to console her crying friend.", "console", 1),
    ("Nothing could console him after the loss.", "console", 1),
    ("He went to console the grieving family.", "console", 1),
    ("Words cannot console those in deep sorrow.", "console", 1),
    ("They gathered to console the widow.", "console", 1),
]

RESUME_CASES = [
    # Index 0: noun /ˈrɛzəmeɪ/ - "submit a resume"
    ("Please send your resume with your application.", "resume", 0),
    ("Her resume lists ten years of experience.", "resume", 0),
    ("Update your resume before the interview.", "resume", 0),
    ("The resume should be no longer than two pages.", "resume", 0),
    ("He attached his resume to the email.", "resume", 0),
    # Index 1: verb /rɪˈzuːm/ - "resume the meeting"
    ("We will resume the meeting after lunch.", "resume", 1),
    ("The game will resume after the rain stops.", "resume", 1),
    ("She plans to resume her studies next year.", "resume", 1),
    ("Normal operations will resume tomorrow.", "resume", 1),
    ("The talks are expected to resume next week.", "resume", 1),
]

# =============================================================================
# EDGE CASES - Harder disambiguation scenarios
# =============================================================================

EDGE_CASES = [
    # === QUESTIONS ===
    # Homograph at sentence start (potential ambiguity with question structure)
    ("Read any good books lately?", "read", 1),  # past tense in question
    ("Does the zoo have elephants?", "does", 0),  # verb, not deer
    ("Will you lead the discussion tomorrow?", "lead", 0),  # verb
    ("Can metal conduct electricity?", "conduct", 1),  # verb
    ("Did she tear the envelope open?", "tear", 1),  # verb (rip)
    ("Is that a live performance?", "live", 1),  # adjective
    ("Should I record this conversation?", "record", 1),  # verb
    ("Would you object to a short break?", "object", 1),  # verb
    ("Have you read the assignment yet?", "read", 1),  # past participle
    ("Did the wind damage the roof?", "wind", 0),  # noun (air)

    # === IMPERATIVES ===
    ("Read this aloud to the class.", "read", 0),  # present imperative
    ("Lead the way, I will follow.", "lead", 0),  # verb imperative
    ("Wind the toy and watch it go.", "wind", 1),  # verb imperative
    ("Record everything they say.", "record", 1),  # verb imperative
    ("Tear here to open the package.", "tear", 1),  # verb imperative
    ("Bow to your partner and begin the dance.", "bow", 1),  # verb imperative
    ("Close the door quietly.", "close", 0),  # verb imperative
    ("Use caution when handling chemicals.", "use", 0),  # verb imperative
    ("Present your findings to the committee.", "present", 1),  # verb imperative
    ("Separate the eggs before mixing.", "separate", 1),  # verb imperative

    # === NEGATIONS ===
    ("I have not read that book.", "read", 1),  # past participle (negated)
    ("She does not live here anymore.", "live", 0),  # verb (reside)
    ("Do not tear the fabric.", "tear", 1),  # verb (rip)
    ("He will not lead the project.", "lead", 0),  # verb
    ("They did not record the meeting.", "record", 1),  # verb
    ("I cannot excuse this behavior.", "excuse", 0),  # verb
    ("We must not desert our allies.", "desert", 1),  # verb (abandon)
    ("You should not subject them to criticism.", "subject", 1),  # verb
    ("She never did read my letter.", "read", 0),  # present tense (emphatic)
    ("The workers refuse to handle the refuse.", "refuse", 1),  # first = verb, asking about first instance

    # === PAST PERFECT / COMPLEX TENSES ===
    ("She had read every book in the library.", "read", 1),  # past participle
    ("The path had wound through the forest for miles.", "wound", 1),  # past of wind
    ("He had never wound a watch before.", "wound", 1),  # past of wind
    ("They had already read the notice.", "read", 1),  # past participle
    ("The bandage had been wound too tightly.", "wound", 1),  # past of wind

    # === MINIMAL CONTEXT (short but unambiguous) ===
    ("I read daily.", "read", 0),  # present tense (habitual)
    ("She read it.", "read", 1),  # past tense (completed action)
    ("Lead pipes.", "lead", 1),  # noun (metal)
    ("Lead us.", "lead", 0),  # verb
    ("Live wire.", "live", 1),  # adjective
    ("I live.", "live", 0),  # verb
    ("The tear fell.", "tear", 0),  # noun (from eye)
    ("Do not tear it.", "tear", 1),  # verb (rip)
    ("A bow tie.", "bow", 0),  # noun (decorative)
    ("Please bow.", "bow", 1),  # verb

    # === SENTENCES WITH MULTIPLE HOMOGRAPH OCCURRENCES ===
    # These use the 4th element (occurrence) to specify which instance (1-indexed)
    ("The bass player caught a bass.", "bass", 0, 1),  # first bass = instrument
    ("The bass player caught a bass.", "bass", 1, 2),  # second bass = fish
    ("Reading about how to read better.", "read", 0, 2),  # second read = present
    ("She read about how people read in ancient times.", "read", 1, 1),  # first read = past
    ("She read about how people read in ancient times.", "read", 0, 2),  # second read = present
    ("The record-breaking athlete will record a new album.", "record", 1, 2),  # second = verb
    ("I object to that object being here.", "object", 1, 1),  # first = verb
    ("I object to that object being here.", "object", 0, 2),  # second = noun
    ("The present I got was to present at the conference.", "present", 0, 1),  # first = noun
    ("The present I got was to present at the conference.", "present", 1, 2),  # second = verb
    ("The rebel decided not to rebel.", "rebel", 0, 1),  # first = noun
    ("The rebel decided not to rebel.", "rebel", 1, 2),  # second = verb
    ("The suspect made us suspect foul play.", "suspect", 0, 1),  # first = noun
    ("The suspect made us suspect foul play.", "suspect", 1, 2),  # second = verb

    # === IDIOMATIC / FIGURATIVE USAGE ===
    ("You reap what you sow.", "sow", 0),  # verb (plant) - idiom
    ("He has a lead on the competition.", "lead", 0),  # noun (advantage) pronounced /liːd/
    ("She wound up in trouble.", "wound", 1),  # phrasal verb (ended up)
    ("The wind picked up.", "wind", 0),  # noun (air)
    ("Close, but no cigar.", "close", 1),  # adjective (near)
    ("That was a close call.", "close", 1),  # adjective (near)
    ("What is the use?", "use", 1),  # noun (purpose)
    ("The project will project success.", "project", 1),  # second = verb
    ("Content with the content.", "content", 1),  # first = adjective
    ("Take a bow for your performance.", "bow", 1),  # verb (bend)

    # === CHILDREN'S BOOK STYLE (simple vocabulary, clear context) ===
    ("The little girl read her favorite book.", "read", 1),  # past
    ("I can read this story by myself.", "read", 0),  # present
    ("The wind blew the leaves away.", "wind", 0),  # noun
    ("Help me wind up the music box.", "wind", 1),  # verb
    ("A white dove flew over the garden.", "dove", 0),  # noun (bird)
    ("The frog dove into the pond.", "dove", 1),  # past of dive
    ("She put a pretty bow on the present.", "bow", 0),  # noun (ribbon)
    ("The prince had to bow to the princess.", "bow", 1),  # verb
    ("Where do the rabbits live?", "live", 0),  # verb (reside)
    ("Is this show live or recorded?", "live", 1),  # adjective
    ("A tear rolled down the puppy's face.", "tear", 0),  # noun
    ("Do not tear the wrapping paper yet.", "tear", 1),  # verb
]

# =============================================================================
# COMBINED TEST CASES
# =============================================================================

# Standard cases: 5 sentences per pronunciation, balanced coverage
STANDARD_CASES = (
    # Vowel/consonant changes
    READ_CASES +
    LEAD_CASES +
    LIVE_CASES +
    WIND_CASES +
    WOUND_CASES +
    TEAR_CASES +
    BOW_CASES +
    ROW_CASES +
    SOW_CASES +
    BASS_CASES +
    CLOSE_CASES +
    USE_CASES +
    HOUSE_CASES +
    EXCUSE_CASES +
    DOVE_CASES +
    DOES_CASES +
    SEWER_CASES +
    POLISH_CASES +
    # Stress-shift
    PRESENT_CASES +
    RECORD_CASES +
    PRODUCE_CASES +
    OBJECT_CASES +
    CONTENT_CASES +
    CONTRACT_CASES +
    REFUSE_CASES +
    DESERT_CASES +
    MINUTE_CASES +
    SEPARATE_CASES +
    ALTERNATE_CASES +
    ATTRIBUTE_CASES +
    ENTRANCE_CASES +
    GRADUATE_CASES +
    BUFFET_CASES +
    PERMIT_CASES +
    CONDUCT_CASES +
    CONFLICT_CASES +
    CONTEST_CASES +
    CONVERT_CASES +
    CONVICT_CASES +
    INSERT_CASES +
    INVALID_CASES +
    PROJECT_CASES +
    REBEL_CASES +
    SUBJECT_CASES +
    SUSPECT_CASES +
    CONSOLE_CASES +
    RESUME_CASES
)

# All cases including edge cases for comprehensive testing
TEST_CASES = list(STANDARD_CASES) + EDGE_CASES

# =============================================================================
# COVERAGE VALIDATION
# =============================================================================

def get_coverage_report() -> dict:
    """Generate a coverage report for all test cases."""
    from collections import defaultdict

    # Standard cases coverage (should be balanced 5/5)
    standard_coverage = defaultdict(lambda: {0: 0, 1: 0})
    for sentence, word, expected in STANDARD_CASES:
        standard_coverage[word.lower()][expected] += 1

    # Edge cases coverage (additional harder cases)
    edge_coverage = defaultdict(lambda: {0: 0, 1: 0})
    for sentence, word, expected in EDGE_CASES:
        edge_coverage[word.lower()][expected] += 1

    # Combined coverage
    total_coverage = defaultdict(lambda: {0: 0, 1: 0})
    for sentence, word, expected in TEST_CASES:
        total_coverage[word.lower()][expected] += 1

    report = {
        "standard_cases": len(STANDARD_CASES),
        "edge_cases": len(EDGE_CASES),
        "total_cases": len(TEST_CASES),
        "homographs_in_standard": len(standard_coverage),
        "homographs_in_edge": len(edge_coverage),
        "homographs_total": len(total_coverage),
        "balanced": [],
        "unbalanced": [],
        "standard_details": {},
        "edge_details": {},
    }

    for word, counts in sorted(standard_coverage.items()):
        report["standard_details"][word] = counts
        if counts[0] == 5 and counts[1] == 5:
            report["balanced"].append(word)
        else:
            report["unbalanced"].append((word, counts))

    for word, counts in sorted(edge_coverage.items()):
        report["edge_details"][word] = counts

    return report


if __name__ == "__main__":
    report = get_coverage_report()

    print("=" * 60)
    print("HOMOGRAPH TEST CORPUS COVERAGE REPORT")
    print("=" * 60)

    print(f"\nStandard cases: {report['standard_cases']}")
    print(f"Edge cases: {report['edge_cases']}")
    print(f"Total test cases: {report['total_cases']}")

    print(f"\nHomographs in standard set: {report['homographs_in_standard']}")
    print(f"Homographs in edge cases: {report['homographs_in_edge']}")

    print(f"\nStandard cases balanced (5/5): {len(report['balanced'])}/{report['homographs_in_standard']}")

    if report["unbalanced"]:
        print("\nUnbalanced homographs in standard set:")
        for word, counts in report["unbalanced"]:
            print(f"  {word}: {counts[0]}/{counts[1]}")
    else:
        print("\nAll standard homographs are balanced (5/5)!")

    print("\nEdge case coverage by homograph:")
    for word, counts in sorted(report["edge_details"].items()):
        total = counts[0] + counts[1]
        print(f"  {word}: {total} cases (idx0: {counts[0]}, idx1: {counts[1]})")
