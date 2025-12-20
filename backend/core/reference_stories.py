"""
Curated reference stories for few-shot examples in story generation.

These are manually cleaned versions of classic children's picture books,
used to show the model what excellent children's prose looks like.

Usage:
    from backend.core.reference_stories import get_random_examples

    # Get 1-2 random example stories formatted for the prompt
    examples = get_random_examples(count=2)
"""

import random
from dataclasses import dataclass


@dataclass
class ReferenceStory:
    """A curated reference story for few-shot examples."""
    title: str
    author: str
    text: str
    word_count: int
    notes: str  # Why this is a good example

    def to_example_string(self) -> str:
        """Format for inclusion in a prompt."""
        return f'''EXAMPLE: "{self.title}" by {self.author}
---
{self.text}
---
({self.word_count} words)'''


# Manually curated reference stories
# Each story is cleaned of duplicates, copyright notices, and metadata

HAROLD_AND_THE_PURPLE_CRAYON = ReferenceStory(
    title="Harold and the Purple Crayon",
    author="Crockett Johnson",
    notes="Classic picture book. Shows episodic adventure structure, simple sentences, "
          "imaginative problem-solving, and a satisfying circular ending.",
    word_count=660,
    text="""One evening, after thinking it over for some time, Harold decided to go for a walk in the moonlight.

There wasn't any moon, and Harold needed a moon for a walk in the moonlight. And he needed something to walk on.

He made a long straight path so he wouldn't get lost. And he set off on his walk, taking his big purple crayon with him.

But he didn't seem to be getting anywhere on the long straight path. So he left the path for a short cut across a field. And the moon went with him.

The short cut led right to where Harold thought a forest ought to be. He didn't want to get lost in the woods. So he made a very small forest, with just one tree in it.

It turned out to be an apple tree. The apples would be very tasty, Harold thought, when they got red.

So he put a frightening dragon under the tree to guard the apples. It was a terribly frightening dragon.

It even frightened Harold. He backed away. His hand holding the purple crayon shook.

Suddenly he realized what was happening. But by then Harold was over his head in an ocean.

He came up thinking fast. And in no time he was climbing aboard a trim little boat.

He quickly set sail. And the moon sailed along with him.

After he had sailed long enough, Harold made land without much trouble. He stepped ashore on the beach, wondering where he was.

The sandy beach reminded Harold of picnics. And the thought of picnics made him hungry. So he laid out a nice simple picnic lunch.

There was nothing but pie. But there were all nine kinds of pie that Harold liked best.

When Harold finished his picnic there was quite a lot left. He hated to see so much delicious pie go to waste.

So Harold left a very hungry moose and a deserving porcupine to finish it up. And off he went, looking for a hill to climb, to see where he was.

Harold knew that the higher up he went, the farther he could see. So he decided to make the hill into a mountain. If he went high enough, he thought, he could see the window of his bedroom.

He was tired and he felt he ought to be getting to bed. He hoped he could see his bedroom window from the top of the mountain.

But as he looked down over the other side he slipped— And there wasn't any other side of the mountain. He was falling, in thin air.

But, luckily, he kept his wits and his purple crayon. He made a balloon and he grabbed on to it.

And he made a basket under the balloon big enough to stand in. He had a fine view from the balloon but he couldn't see his window. He couldn't even see a house.

So he made a house, with windows. And he landed the balloon on the grass in the front yard.

None of the windows was his window. He tried to think where his window ought to be.

He made some more windows. He made a big building full of windows.

He made lots of buildings full of windows. He made a whole city full of windows.

But none of the windows was his window. He couldn't think where it might be.

He decided to ask a policeman. The policeman pointed the way Harold was going anyway. But Harold thanked him.

And he walked along with the moon, wishing he was in his room and in bed. Then, suddenly, Harold remembered.

He remembered where his bedroom window was, when there was a moon. It was always right around the moon.

And then Harold made his bed. He got in it and he drew up the covers.

The purple crayon dropped on the floor. And Harold dropped off to sleep."""
)


LAST_STOP_ON_MARKET_STREET = ReferenceStory(
    title="Last Stop on Market Street",
    author="Matt de la Peña",
    notes="Caldecott Honor, Newbery Medal. Shows dialogue-driven narrative, "
          "emotional depth, sensory details, and theme emerging through character.",
    word_count=580,
    text="""CJ pushed through the church doors and skipped down the steps. The outside air smelled like freedom, but it also smelled like rain, which freckled CJ's shirt and dripped down his nose.

He ducked under his nana's umbrella, saying, "How come we gotta wait for the bus in all this wet?"

"Trees get thirsty, too," his nana told him. "Don't you see that big one drinking through a straw?"

CJ looked for a long time but never saw a straw.

From the bus stop, he watched water pool on flower petals. Watched rain patter against the windshield of a nearby car. His friend Colby climbed in, gave CJ a wave, and drove off with his dad.

"Nana, how come we don't got a car?"

"Boy, what do we need a car for? We got a bus that breathes fire, and old Mr. Dennis, who always has a trick for you."

The bus creaked to a stop in front of them. It sighed and sagged and the doors swung open.

"What's that I see?" Mr. Dennis asked. He pulled a coin from behind CJ's ear and placed it in his palm. Nana laughed her deep laugh and pushed CJ along.

They sat right up front. The man across the way was tuning a guitar. An old woman with curlers had butterflies in a jar. Nana gave everyone a great big smile and a "good afternoon." She made sure CJ did the same.

The bus lurched forward and stopped, lurched forward and stopped. Nana hummed as she knit.

"How come we always gotta go here after church?" CJ said. "Miguel and Colby never have to go nowhere."

"I feel sorry for those boys," she told him. "They'll never get a chance to meet Bobo or the Sunglass Man. And I hear Trixie got herself a brand-new hat."

CJ stared out the window feeling sorry for himself.

A man climbed aboard with a spotted dog. CJ gave up his seat. "How come that man can't see?"

"Boy, what do you know about seeing?" Nana told him. "Some people watch the world with their ears."

"That's a fact. Their noses, too," the man said, sniffing at the air. "That's a mighty fine perfume you're wearing today, ma'am."

Nana squeezed the man's hand and laughed her deep laugh.

Two older boys got on next. CJ watched as they moved on by and stood in back.

"Sure wish I had one of those," he said.

Nana set down her knitting. "What for? You got the real live thing sitting across from you. Why don't you ask the man if he'll play us a song?"

CJ didn't have to. The guitar player was already plucking strings and beginning to sing.

"To feel the magic of music," the blind man whispered, "I like to close my eyes."

Nana closed hers, too. So did CJ and the spotted dog.

And in the darkness, the rhythm lifted CJ out of the bus, out of the busy city. He saw sunset colors swirling over crashing waves. Saw a family of hawks slicing through the sky. Saw the old woman's butterflies dancing free in the light of the moon.

CJ's chest grew full and he was lost in the sound and the sound gave him the feeling of magic.

"Last stop on Market Street," Mr. Dennis called.

CJ looked around as he stepped off the bus. Crumbling sidewalks and broken-down doors, graffiti-tagged windows and boarded-up stores. He reached for his nana's hand.

"How come it's always so dirty over here?"

She smiled and pointed to the sky. "Sometimes when you're surrounded by dirt, CJ, you're a better witness for what's beautiful."

CJ saw the perfect rainbow arcing over their soup kitchen."""
)


FROG_AND_TOAD_SPRING = ReferenceStory(
    title="Spring",
    author="Arnold Lobel (from Frog and Toad Are Friends)",
    notes="Shows clever problem-solving, friendship dynamics, simple dialogue-driven "
          "narrative, and a satisfying twist ending.",
    word_count=390,
    text="""Frog ran up the path to Toad's house. He knocked on the front door. There was no answer.

"Toad, Toad," shouted Frog, "wake up. It is spring!"

"Blah," said a voice from inside the house.

"Toad, Toad," cried Frog. "The sun is shining! The snow is melting. Wake up!"

"I am not here," said the voice.

Frog walked into the house. It was dark. All the shutters were closed.

"Toad, where are you?" called Frog.

"Go away," said the voice from a corner of the room.

Toad was lying in bed. He had pulled all the covers over his head. Frog pushed Toad out of bed. He pushed him out of the house and onto the front porch. Toad blinked in the bright sun.

"Help!" said Toad. "I cannot see anything."

"Don't be silly," said Frog. "What you see is the clear warm light of April. And it means that we can begin a whole new year together, Toad. Think of it," said Frog. "We will skip through the meadows and run through the woods and swim in the river. In the evenings we will sit right here on this front porch and count the stars."

"You can count them, Frog," said Toad. "I will be too tired. I am going back to bed."

Toad went back into the house. He got into the bed and pulled the covers over his head again.

"But, Toad," cried Frog, "you will miss all the fun!"

"Listen, Frog," said Toad. "How long have I been asleep?"

"You have been asleep since November," said Frog.

"Well then," said Toad, "a little more sleep will not hurt me. Come back again and wake me up at about half past May. Good night, Frog."

"But, Toad," said Frog, "I will be lonely until then."

Toad did not answer. He had fallen asleep.

Frog looked at Toad's calendar. The November page was still on top. Frog tore off the November page. He tore off the December page. And the January page, the February page, and the March page. He came to the April page. Frog tore off the April page too.

Then Frog ran back to Toad's bed. "Toad, Toad, wake up. It is May now."

"What?" said Toad. "Can it be May so soon?"

"Yes," said Frog. "Look at your calendar."

Toad looked at the calendar. The May page was on top.

"Why, it is May!" said Toad as he climbed out of bed.

Then he and Frog ran outside to see how the world was looking in the spring."""
)


FROG_AND_TOAD_THE_LETTER = ReferenceStory(
    title="The Letter",
    author="Arnold Lobel (from Frog and Toad Are Friends)",
    notes="Touching story about friendship, shows emotional depth through simple "
          "actions, building anticipation, and a heartwarming resolution.",
    word_count=420,
    text="""Toad was sitting on his front porch. Frog came along and said, "What is the matter, Toad? You are looking sad."

"Yes," said Toad. "This is my sad time of day. It is the time when I wait for the mail to come. It always makes me very unhappy."

"Why is that?" asked Frog.

"Because I never get any mail," said Toad.

"Not ever?" asked Frog.

"No, never," said Toad. "No one has ever sent me a letter. Every day my mailbox is empty. That is why waiting for the mail is a sad time for me."

Frog and Toad sat on the porch, feeling sad together.

Then Frog said, "I have to go home now, Toad. There is something that I must do."

Frog hurried home. He found a pencil and a piece of paper. He wrote on the paper. He put the paper in an envelope. On the envelope he wrote "A LETTER FOR TOAD."

Frog ran out of his house. He saw a snail that he knew.

"Snail," said Frog, "please take this letter to Toad's house and put it in his mailbox."

"Sure," said the snail. "Right away."

Then Frog ran back to Toad's house. Toad was in bed, taking a nap.

"Toad," said Frog, "I think you should get up and wait for the mail some more."

"No," said Toad, "I am tired of waiting for the mail."

Frog looked out of the window at Toad's mailbox. The snail was not there yet.

"Toad," said Frog, "you never know when someone may send you a letter."

"No, no," said Toad. "I do not think anyone will ever send me a letter."

Frog looked out of the window. The snail was not there yet.

"But, Toad," said Frog, "someone may send you a letter today."

"Don't be silly," said Toad. "No one has ever sent me a letter before, and no one will send me a letter today."

Frog looked out of the window. The snail was still not there.

"Frog, why do you keep looking out of the window?" asked Toad.

"Because now I am waiting for the mail," said Frog.

"But there will not be any," said Toad.

"Oh, yes there will," said Frog, "because I have sent you a letter."

"You have?" said Toad. "What did you write in the letter?"

Frog said, "I wrote 'Dear Toad, I am glad that you are my best friend. Your best friend, Frog.'"

"Oh," said Toad, "that makes a very good letter."

Then Frog and Toad went out onto the front porch to wait for the mail. They sat there, feeling happy together.

Frog and Toad waited a long time. Four days later the snail got to Toad's house and gave him the letter from Frog. Toad was very pleased to have it."""
)


FROG_AND_TOAD_A_SWIM = ReferenceStory(
    title="A Swim",
    author="Arnold Lobel (from Frog and Toad Are Friends)",
    notes="Humorous story about vulnerability and self-acceptance, escalating comedy, "
          "shows character through actions and reactions.",
    word_count=430,
    text="""Toad and Frog went down to the river.

"What a day for a swim," said Frog.

"Yes," said Toad. "I will go behind these rocks and put on my bathing suit."

"I don't wear a bathing suit," said Frog.

"Well, I do," said Toad. "After I put on my bathing suit, you must not look at me until I get into the water."

"Why not?" asked Frog.

"Because I look funny in my bathing suit. That is why," said Toad.

Frog closed his eyes when Toad came out from behind the rocks. Toad was wearing his bathing suit.

"Don't peek," he said.

Frog and Toad jumped into the water. They swam all afternoon. Frog swam fast and made big splashes. Toad swam slowly and made smaller splashes.

A turtle came along the riverbank.

"Frog, tell that turtle to go away," said Toad. "I do not want him to see me in my bathing suit when I come out of the river."

Frog swam over to the turtle.

"Turtle," said Frog, "you will have to go away."

"Why should I?" asked the turtle.

"Because Toad thinks that he looks funny in his bathing suit, and he does not want you to see him," said Frog.

Some lizards were sitting nearby.

"Does Toad really look funny in his bathing suit?" they asked.

A snake crawled out of the grass.

"If Toad looks funny in his bathing suit," said the snake, "then I, for one, want to see him."

"We want to see him too," said two dragonflies.

"Me too," said a field mouse. "I have not seen anything funny in a long time."

Frog swam back to Toad.

"I am sorry, Toad," he said. "Everyone wants to see how you will look."

"Then I will stay right here until they go away," said Toad.

The turtle and the lizards and the snake and the dragonflies and the field mouse all sat on the riverbank. They waited for Toad to come out of the water.

"Please," cried Frog, "please go away!"

But no one went away.

Toad was getting colder and colder. He was beginning to shiver and sneeze.

"I will have to come out of the water," said Toad. "I am catching a cold."

Toad climbed out of the river. The water dripped out of his bathing suit and down onto his feet.

The turtle laughed. The lizards laughed. The snake laughed. The field mouse laughed, and Frog laughed.

"What are you laughing at, Frog?" said Toad.

"I am laughing at you, Toad," said Frog, "because you do look funny in your bathing suit."

"Of course I do," said Toad.

Then he picked up his clothes and went home."""
)


# All available reference stories
ALL_REFERENCE_STORIES = [
    HAROLD_AND_THE_PURPLE_CRAYON,
    LAST_STOP_ON_MARKET_STREET,
    FROG_AND_TOAD_SPRING,
    FROG_AND_TOAD_THE_LETTER,
    FROG_AND_TOAD_A_SWIM,
]


def get_random_examples(count: int = 2, seed: int = None) -> list[ReferenceStory]:
    """
    Get random reference stories for few-shot examples.

    Args:
        count: Number of examples to return (1-2 recommended)
        seed: Optional random seed for reproducibility

    Returns:
        List of ReferenceStory objects
    """
    if seed is not None:
        random.seed(seed)

    count = min(count, len(ALL_REFERENCE_STORIES))
    return random.sample(ALL_REFERENCE_STORIES, count)


def format_examples_for_prompt(count: int = 2, seed: int = None) -> str:
    """
    Get formatted example stories ready to include in a prompt.

    Args:
        count: Number of examples to include
        seed: Optional random seed for reproducibility

    Returns:
        Formatted string with example stories
    """
    examples = get_random_examples(count=count, seed=seed)

    formatted = ["Here are examples of excellent children's picture book prose:\n"]
    for i, story in enumerate(examples, 1):
        formatted.append(f"\n{story.to_example_string()}\n")

    return "\n".join(formatted)
