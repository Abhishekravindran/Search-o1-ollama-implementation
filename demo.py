from typing import Tuple, Dict, Any, List
import pickle
import re

from langchain.prompts.chat import HumanMessagePromptTemplate
from langchain.schema import (
    AIMessage,
    HumanMessage,
    ChatMessage,
)

FEWSHOTS = ["""Question: What is the elevation range for the area that the eastern sector of the Colorado orogeny extends into?
Thought 1: I need to search Colorado orogeny, find the area that the eastern sector of the Colorado orogeny extends into, then find the elevation range of the area.
Action 1: Search[Colorado orogeny]
Observation 1: The Colorado orogeny was an episode of mountain building (an orogeny) in Colorado and surrounding areas.
Thought 2: It does not mention the eastern sector. So I need to look up eastern sector.
Action 2: Lookup[eastern sector]
Observation 2: (Result 1 / 1) The eastern sector extends into the High Plains and is called the Central Plains orogeny.
Thought 3: The eastern sector of Colorado orogeny extends into the High Plains. So I need to search High Plains and find its elevation range.
Action 3: Search[High Plains]
Observation 3: High Plains refers to one of two distinct land regions:
Thought 4: I need to instead search High Plains (United States).
Action 4: Search[High Plains (United States)]
Observation 4: The High Plains are a subregion of the Great Plains. From east to west, the High Plains rise in elevation from around 1,800 to 7,000 ft (550 to 2,130 m).[3]
Thought 5: High Plains rise in elevation from around 1,800 to 7,000 ft, so the answer is 1,800 to 7,000 ft.
Action 5: Finish[1,800 to 7,000 ft]""",
"""Question: Musician and satirist Allie Goertz wrote a song about the "The Simpsons" character Milhouse, who Matt Groening named after who?
Thought 1: The question simplifies to "The Simpsons" character Milhouse is named after who. I only need to search Milhouse and find who it is named after.
Action 1: Search[Milhouse]
Observation 1: Milhouse Mussolini Van Houten is a recurring character in the Fox animated television series The Simpsons voiced by Pamela Hayden and created by Matt Groening.
Thought 2: The paragraph does not tell who Milhouse is named after, maybe I can look up "named after".
Action 2: Lookup[named after]
Observation 2: (Result 1 / 1) Milhouse was named after U.S. president Richard Nixon, whose middle name was Milhous. 
Thought 3: Milhouse was named after U.S. president Richard Nixon, so the answer is Richard Nixon.
Action 3: Finish[Richard Nixon]""",
"""Question: Which documentary is about Finnish rock groups, Adam Clayton Powell or The Saimaa Gesture?
Thought 1: I need to search Adam Clayton Powell and The Saimaa Gesture, and find which documentary is about Finnish rock groups.
Action 1: Search[Adam Clayton Powell]
Observation 1: Could not find [Adam Clayton Powell]. Similar: ['Adam Clayton Powell III', 'Seventh Avenue (Manhattan)', 'Adam Clayton Powell Jr. State Office Building', 'Isabel Washington Powell', 'Adam Powell', 'Adam Clayton Powell (film)', 'Giancarlo Esposito'].
Thought 2: To find the documentary, I can search Adam Clayton Powell (film).
Action 2: Search[Adam Clayton Powell (film)]
Observation 2: Adam Clayton Powell is a 1989 American documentary film directed by Richard Kilberg.
The film is about the rise and fall of influential African-American politician Adam Clayton Powell Jr.[3][4] It was later aired as part of the PBS series The American Experience.
Thought 3: Adam Clayton Powell (film) is a documentary about an African-American politician, not Finnish rock groups. So the documentary about Finnish rock groups must instead be The Saimaa Gesture.
Action 3: Finish[The Saimaa Gesture]""",
"""Question: What profession does Nicholas Ray and Elia Kazan have in common?
Thought 1: I need to search Nicholas Ray and Elia Kazan, find their professions, then find the profession they have in common.
Action 1: Search[Nicholas Ray]
Observation 1: Nicholas Ray (born Raymond Nicholas Kienzle Jr., August 7, 1911 – June 16, 1979) was an American film director, screenwriter, and actor best known for the 1955 film Rebel Without a Cause.
Thought 2: Professions of Nicholas Ray are director, screenwriter, and actor. I need to search Elia Kazan next and find his professions.
Action 2: Search[Elia Kazan]
Observation 2: Elia Kazan was an American film and theatre director, producer, screenwriter and actor.
Thought 3: Professions of Elia Kazan are director, producer, screenwriter, and actor. So profession Nicholas Ray and Elia Kazan have in common is director, screenwriter, and actor.
Action 3: Finish[director, screenwriter, actor]""",
"""Question: Which magazine was started first Arthur's Magazine or First for Women?
Thought 1: I need to search Arthur's Magazine and First for Women, and find which was started first.
Action 1: Search[Arthur's Magazine]
Observation 1: Arthur's Magazine (1844-1846) was an American literary periodical published in Philadelphia in the 19th century. 
Thought 2: Arthur's Magazine was started in 1844. I need to search First for Women next.
Action 2: Search[First for Women]
Observation 2: First for Women is a woman's magazine published by Bauer Media Group in the USA.[1] The magazine was started in 1989. 
Thought 3: First for Women was started in 1989. 1844 (Arthur's Magazine) < 1989 (First for Women), so Arthur's Magazine was started first.
Action 3: Finish[Arthur's Magazine]""",
"""Question: Were Pavel Urysohn and Leonid Levin known for the same type of work?
Thought 1: I need to search Pavel Urysohn and Leonid Levin, find their types of work, then find if they are the same.
Action 1: Search[Pavel Urysohn]
Observation 1: Pavel Samuilovich Urysohn (February 3, 1898 â August 17, 1924) was a Soviet mathematician who is best known for his contributions in dimension theory.
Thought 2: Pavel Urysohn is a mathematician. I need to search Leonid Levin next and find its type of work.
Action 2: Search[Leonid Levin]
Observation 2: Leonid Anatolievich Levin is a Soviet-American mathematician and computer scientist. 
Thought 3: Leonid Levin is a mathematician and computer scientist. So Pavel Urysohn and Leonid Levin have the same type of work. 
Action 3: Finish[yes]"""]

REFLECTION_FEWSHOTS = [
"""
Previous Trial:
Question: The Rome Protocols were signed by three Prime Ministers one of which was assassinated as part of what?
Thought 1: I need to search Rome Protocols, find the three Prime Ministers, then find what they were assassinated as part of.
Action 1: Search[Rome Protocols]
Observation 1: The Rome Protocols were a series of three international agreements concluded in Rome on 17 March 1934 between the governments of Austria, Hungary and Italy. They were signed by Italian Prime Minister Benito Mussolini, Austrian Chancellor Engelbert Dollfuss and Hungarian Prime Minister Gyula Gömbös. All of the protocols went into effect on 12 July 1934 and were registered in League of Nations Treaty Series on 12 December 1934.
Thought 2: The three Prime Ministers were Benito Mussolini, Engelbert Dollfuss, and Gyula Gömbös. I need to search Benito Mussolini and find what he was assassinated as part of.
Action 2: Search[Benito Mussolini]
Observation 2: Benito Amilcare Andrea Mussolini (UK:  MU(U)SS-ə-LEE-nee, US:  MOOSS-, Italian: [beˈniːto aˈmilkare anˈdrɛːa mussoˈliːni]; 29 July 1883 – 28 April 1945) was an Italian politician and journalist who founded and led the National Fascist Party (PNF). He was Prime Minister of Italy from the March on Rome in 1922 until his deposition in 1943, as well as "Duce" of Italian fascism from the establishment of the Italian Fasces of Combat in 1919 until his summary execution in 1945 by Italian partisans. As dictator of Italy and principal founder of fascism, Mussolini inspired and supported the international spread of fascist movements during the inter-war period.Mussolini was originally a socialist politician and a journalist at the Avanti! newspaper. In 1912, he became a member of the National Directorate of the Italian Socialist Party (PSI), but he was expelled from the PSI for advocating military intervention in World War I, in opposition to the party's stance on neutrality. In 1914, Mussolini founded a new journal, Il Popolo d'Italia, and served in the Royal Italian Army during the war until he was wounded and discharged in 1917. Mussolini denounced the PSI, his views now centering on Italian nationalism instead of socialism, and later founded the fascist movement which came to oppose egalitarianism and class conflict, instead advocating "revolutionary nationalism" transcending class lines. On 31 October 1922, following the March on Rome (28–30 October), Mussolini was appointed prime minister by King Victor Emmanuel III, becoming the youngest individual to hold the office up to that time. After removing all political opposition through his secret police and outlawing labor strikes, Mussolini and his followers consolidated power through a series of laws that transformed the nation into a one-party dictatorship. Within five years, Mussolini had established dictatorial authority by both legal and illegal means and aspired to create a totalitarian state. In 1929, Mussolini signed the Lateran Treaty with the Holy See to establish Vatican City.
Mussolini's foreign policy aimed to restore the ancient grandeur of the Roman Empire by expanding Italian colonial possessions and the fascist sphere of influence. In the 1920s, he ordered the Pacification of Libya, instructed the bombing of Corfu over an incident with Greece, established a protectorate over Albania, and incorporated the city of Fiume into the Italian state via agreements with Yugoslavia. In 1936, Ethiopia was conquered following the Second Italo-Ethiopian War and merged into Italian East Africa (AOI) with Eritrea and Somalia. In 1939, Italian forces annexed Albania. Between 1936 and 1939, Mussolini ordered the successful Italian military intervention in Spain in favor of Francisco Franco during the Spanish Civil War. Mussolini's Italy initially tried to avoid the outbreak of a second global war, sending troops at the Brenner Pass to delay Anschluss and taking part in the Stresa Front, the Lytton Report, the Treaty of Lausanne, the Four-Power Pact and the Munich Agreement. However, Italy then alienated itself from Britain and France by aligning with Germany and Japan. Germany invaded Poland on 1 September 1939, resulting in declarations of war by France and the UK and the start of World War II.
On 10 June 1940, Mussolini decided to enter the war on the Axis side. Despite initial success, the subsequent Axis collapse on multiple fronts and eventual Allied invasion of Sicily made Mussolini lose the support of the population and members of the Fascist Party. As a consequence, early on 25 July 1943, the Grand Council of Fascism passed a motion of no confidence in Mussolini; later that day King Victor Emmanuel III dismissed him as head of government and had him placed in custody, appointing Pietro Badoglio to succeed him as Prime Minister. After the king agreed to an armistice with the Allies, on 12 September 1943 Mussolini was rescued from captivity in the Gran Sasso raid by German paratroopers and Waffen-SS commandos led by Major Otto-Harald Mors. Adolf Hitler, after meeting with the rescued former dictator, then put Mussolini in charge of a puppet regime in northern Italy, the Italian Social Republic (Italian: Repubblica Sociale Italiana, RSI), informally known as the Salò Republic, causing a civil war. In late April 1945, in the wake of near total defeat, Mussolini and his mistress Clara Petacci attempted to flee to Switzerland, but both were captured by Italian communist partisans and summarily executed by firing squad on 28 April 1945 near Lake Como. The bodies of Mussolini and his mistress were then taken to Milan, where they were hung upside down at a service station to publicly confirm their demise.
Thought 3: Benito Mussolini was assassinated as part of the collapse of the Axis powers during World War II. So the Rome Protocols were signed by three Prime Ministers one of which was assassinated as part of World War II.
Action 3: Finish[World War II]

Reflection: I searched one of the prime ministers involved in the signing, then attemted to answer right away. I should have searched each of the prime ministers, then looked up 'death' on each of their pages in order to get more information before answering.
""",
"""
Previous Trial:
Question: Kam Heskin plays Paige Morgan in a 2004 film directed by who?
Thought 1: I need to search Kam Heskin and Paige Morgan, find the 2004 film they are in, then find the director of the film.
Action 1: Search[Kam Heskin]
Observation 1: Kam Erika Heskin (born May 8, 1973) is an American actress. She began her career playing Caitlin Deschanel on the NBC daytime soap opera Sunset Beach (1998–1999), before appearing in films Planet of the Apes (2001) and Catch Me If You Can (2002). Heskin went on in 2003 to play Elizabeth Bennet in an independent film Pride & Prejudice: A Latter-Day Comedy, Robin in Charmed (2004),  and Paige Morgan in The Prince and Me film franchise (2006–2010).
Thought 2: Kam Heskin plays Paige Morgan in The Prince and Me film franchise. I need to search The Prince and Me film franchise and find the director of the 2004 film.
Action 2: Search[The Prince and Me film franchise]
Observation 2: Could not find [The Prince and Me film franchise]. Similar: ['Kam Heskin', 'Prince of Persia', 'Harry Potter and the Half-Blood Prince (film)', 'Prince of Persia: The Sands of Time (film)', 'The Chronicles of Narnia (film series)', 'Majestic Prince (franchise)', 'Kingsman (franchise)', 'The Little Prince (2015 film)', 'Shrek (franchise)', 'Harry Potter (film series)']
Thought 3: I need to search The Prince and Me (2004 film) instead.
Action 3: Search[The Prince and Me (2004 film)]
Observation 3: Could not find [The Prince and Me (2004 film)]. Similar: ['The Prince & Me', 'The Prince & Me 2: The Royal Wedding', 'Kam Heskin', 'Prince of Darkness (film)', 'Prince of Persia: The Sands of Time (film)', 'Rob Knox', 'Alexander (2004 film)', 'Prince of Persia', 'Brooklynn Prince', 'Prince (musician)']
Thought 4: I need to search The Prince & Me (2004 film).
Action 4: Search[The Prince & Me (2004 film)]
Observation 4: Could not find [The Prince & Me (2004 film)]. Similar: ['The Prince & Me', 'The Prince & Me 2: The Royal Wedding', 'Prince of Darkness (film)', 'Prince of Persia: The Sands of Time (film)', 'Rob Knox', 'Alexander (2004 film)', 'Prince (musician)', 'Prince of Persia', 'Kam Heskin', 'Brooklynn Prince']
Thought 5: I need to search The Prince & Me (2004 film) instead.
Action 5: Search[The Prince & Me (2004 film)]
Observation 5: Could not find [The Prince & Me (2004 film)]. Similar: ['The Prince & Me', 'The Prince & Me 2: The Royal Wedding', 'Prince of Darkness (film)', 'Prince of Persia: The Sands of Time (film)', 'Rob Knox', 'Alexander (2004 film)', 'Prince (musician)', 'Prince of Persia', 'Kam Heskin', 'Brooklynn Prince']
Thought 6: I need to search The Prince & Me (2004 film).
Action 6: Search[The Prince & Me (2004 film)]
Observation 6: Could not find [The Prince & Me (2004 film)]. Similar: ['The Prince & Me', 'The Prince & Me 2: The Royal Wedding', 'Prince of Darkness (film)', 'Prince of Persia: The Sands of Time (film)', 'Rob Knox', 'Alexander (2004 film)', 'Prince (musician)', 'Prince of Persia', 'Kam Heskin', 'Brooklynn Prince']

Reflection: I got stuck in a loop where I kept trying to search 'The Prince & Me (2004 film)' but the page could not be found. Instead I should have tried to search the similar results that had a similar name to see and they were made in 2004.
"""]

SYSTEM_INSTRUCTION = """Solve a question answering task with interleaving Thought, Action, Observation steps. Thought can reason about the current situation, and Action can be three types:
(1) Search[entity], which searches the exact entity on Wikipedia and returns the first paragraph if it exists. If not, it will return some similar entities to search.
(2) Lookup[keyword], which returns the next sentence containing keyword in the last passage successfully found by Search.
(3) Finish[answer], which returns the answer and finishes the task.
"""

human_instruction_template = """{instruction}You may take maximum of {max_steps} steps.
Here are some examples:"""

HUMAN_INSTRUCTION = HumanMessagePromptTemplate.from_template(human_instruction_template)

human_instruction_reflection_template = """Here are some examples:"""
HUMAN_REFLECTION_INSTRUCTION = HumanMessagePromptTemplate.from_template(human_instruction_reflection_template)

SYSTEM_CRITIQUE_EXISTING_RULES_INSTRUCTION = """You will be given two previous task trials in which you were given access to a Docstore API environment and a question to answer: one successful and one unsuccessful trial. You failed the trial either because you guessed the wrong answer with Finish[<answer>], or you used up your set number of reasoning steps."""
SYSTEM_CRITIQUE_ALL_SUCCESS_EXISTING_RULES_INSTRUCTION = """You will be given successful tasks trials in which you were given access to a Docstore API environment and a question to answer."""
SYSTEM_REFLECTION_INSTRUCTION = """You will be given a previous reasoning trial in which you were given access to a Docstore API environment and a question to answer. You were unsuccessful in answering the question either because you guessed the wrong answer with Finish[<answer>], or you used up your set number of reasoning steps. In a few sentences, Diagnose a possible reason for failure and devise a new, concise, high level plan that aims to mitigate the same failure. Use complete sentences."""

def LLM_PARSER(llm_output, step: int, ai_message: bool) -> Tuple[ChatMessage, str, Dict[str, Any]]:
    # First check for <think> tags
    think_pattern = r'<think>(.*?)</think>'
    think_match = re.search(think_pattern, llm_output, re.DOTALL)
    
    if think_match:
        # Extract the thought content
        thought_content = think_match.group(1).strip()
        content = f"Thought {step}: {thought_content}"
        return (
            AIMessage(content=content) if ai_message else HumanMessage(content=content),
            'thought',
            {}
        )

    # Check for action pattern
    pattern = r'(?i)action\s*(?:\d+|)\s*(?::|)\s*'
    action_pattern = r'(?i)\w+\[[^\]]+(?:\]|)'

    match = re.match(pattern, llm_output)
    if match:
        action = llm_output[match.end():]
        content = f"Action {step}: {action}"

        if len(re.findall(action_pattern, action)) > 1:
            return (
                AIMessage(content=content) if ai_message else HumanMessage(content=content),
                'action',
                {'action': ''} # triggers invalid action
            )

        return (
            AIMessage(content=content) if ai_message else HumanMessage(content=content),
            'action',
            {'action': action}
        )

    actions = re.findall(action_pattern, llm_output)
    if len(actions) == 1:
        action = actions[0]
        if action[-1] != ']':
            action += ']'
        content = f"Action {step}: {action}"
        return (
            AIMessage(content=content) if ai_message else HumanMessage(content=content),
            'action',
            {'action': action}
        )
    
    if len(actions) > 1:
        content = re.sub(r"(?i)action\s*(?:\d*|)\s*(?::|)", "", llm_output)
        return (
            AIMessage(content=f"Action {step}: {content}"),
            'action',
            {'action': ''} # triggers invalid action
        )

    # Check for thought pattern
    thought_pattern = r'(?i)thought\s*(?:\d+|)\s*(?::|)\s*(.*)'
    match = re.match(thought_pattern, llm_output)
    if match:
        # Extract the thought word and content
        thought_word = match.group(1)
        content = f"Thought {step}: {thought_word.rstrip(':')}"
    else:
        # If no specific pattern matches, treat as a thought
        content = f"Thought {step}: {llm_output.rstrip(':')}"
    return (
        AIMessage(content=content) if ai_message else HumanMessage(content=content),
        'thought',
        {}
    )

def OBSERVATION_FORMATTER(observation: str, step: int, *args, **kwargs) -> Tuple[ChatMessage, str]:
    return HumanMessage(content=f"Observation {step}: " + observation.rstrip(':')), 'append'

def STEP_IDENTIFIER(line: str) -> str:
    line = line.strip()
    pattern = re.compile(r'^(?i)action(?:\s+(\d+))?:')
    match = pattern.match(line)
    if match:
        return 'action'
    pattern = re.compile(r'^(?i)observation(?:\s+(\d+))?:')
    match = pattern.match(line)
    if match:
        return 'observation'
    return 'thought'

def CYCLER(lines: str) -> List[str]:
    new_lines = []
    scratch_pad = ''
    for line in lines.split('\n'):

        # line is action
        pattern = re.compile(r'^(?i)action(?:\s+(\d+))?:')
        match = pattern.match(line)
        if match:
            if scratch_pad != '':
                new_lines.append(scratch_pad.strip())
                scratch_pad = ''
            new_lines.append(line)
            continue

        # line is thought
        pattern = re.compile(r'^(?i)thought(?:\s+(\d+))?:')
        match = pattern.match(line)
        if match:
            if scratch_pad != '':
                new_lines.append(scratch_pad.strip())
                scratch_pad = ''
            new_lines.append(line)
            continue

        # step is observation
        scratch_pad += line + '\n'

    # the rest of the scratch pad
    if scratch_pad != '':
        new_lines.append(scratch_pad.strip())
    return new_lines

REFLECTION_PREFIX = '\nReflection:'
def PREVIOUS_TRIALS_FORMATTER(reflections: List[str], include_prefix: bool = True) -> str:
    if reflections == []:
        return ''
    if include_prefix:
        memory_prefix = "You have attempted to solve the task before but failed. The following reflection(s) give a plan to avoid failing the task in the same way you did previously. Use them to improve your strategy of solving the task successfully."
    else:
        memory_prefix = ''
    memory_prefix += '\nReflections:'
    for reflection in reflections:
        memory_prefix += f"\n- {reflection.strip()}"
    return memory_prefix

def STEP_STRIPPER(step: str, step_type: str):
    if step_type == 'observation':
        return re.sub(r'^(?i)observation(?:\s+(\d+))?:', 'Observation:', step)
    if step_type == 'action':
        return re.sub(r'^(?i)action(?:\s+(\d+))?:', 'Action:', step)
    if step_type == 'thought':
        return re.sub(r'^(?i)thought(?:\s+(\d+))?:', 'Thought:', step)
    return step








from typing import Tuple, Dict, Any, List
import pickle
import re

from langchain.prompts.chat import HumanMessagePromptTemplate
from langchain.schema import (
    AIMessage,
    HumanMessage,
    ChatMessage,
)


SYSTEM_INSTRUCTION = """Solve a question answering task with interleaving think, Action, Observation steps. think can reason about the current situation, and Action can be three types:
(1) Search[entity], which searches the exact entity on Wikipedia and returns the first paragraph if it exists. If not, it will return some similar entities to search.
(2) Lookup[keyword], which returns the next sentence containing keyword in the last passage successfully found by Search.
(3) Finish[answer], which returns the answer and finishes the task.
Guidelines:
- Break down complex questions into smaller parts
- Use natural language in your queries
- Explain your reasoning before each action
- Submit answers only when you're confident
- Format your final answer as \boxed{YOUR_ANSWER}

"""

FEWSHOTS = ["""
Question: What is the elevation range for the area that the eastern sector of the Colorado orogeny extends into?
think: I need to search Colorado orogeny, find the area that the eastern sector of the Colorado orogeny extends into, then find the elevation range of the area.
<|begin_search_query|>Colorado orogeny<|end_search_query|>
<|begin_search_result|>The Colorado orogeny was an episode of mountain building (an orogeny) in Colorado and surrounding areas.<|end_search_result|>
think: It does not mention the eastern sector. So I need to look up eastern sector.
<|begin_lookup_query|>eastern sector<|end_lookup_query|>
<|begin_lookup_result|>The eastern sector extends into the High Plains and is called the Central Plains orogeny.<|end_lookup_result|>
think: The eastern sector of Colorado orogeny extends into the High Plains. So I need to search High Plains and find its elevation range.
<|begin_search_query|>High Plains elevation range<|end_search_query|>
<|begin_search_result|>The High Plains are a subregion of the Great Plains. From east to west, the High Plains rise in elevation from around 1,800 to 7,000 ft (550 to 2,130 m).<|end_search_result|>
think: High Plains rise in elevation from around 1,800 to 7,000 ft, so the answer is 1,800 to 7,000 ft.
<|begin_answer|>1,800 to 7,000 ft<|end_answer|>
"""]
# reflectionfewshot
REFLECTION_FEWSHOTS = [
"""
Previous Trial:
Question: The Rome Protocols were signed by three Prime Ministers one of which was assassinated as part of what?

think: I need to search Rome Protocols, find the three Prime Ministers, then find what they were assassinated as part of.
<|begin_search_query|>Rome Protocols<|end_search_query|>
<|begin_search_result|>The Rome Protocols were a series of three international agreements concluded in Rome on 17 March 1934 between the governments of Austria, Hungary and Italy. They were signed by Italian Prime Minister Benito Mussolini, Austrian Chancellor Engelbert Dollfuss and Hungarian Prime Minister Gyula Gömbös.<|end_search_result|>

think: The three Prime Ministers were Benito Mussolini, Engelbert Dollfuss, and Gyula Gömbös. I need to search Benito Mussolini and find what he was assassinated as part of.
<|begin_search_query|>Benito Mussolini assassination<|end_search_query|>
<|begin_search_result|>Benito Mussolini was executed by Italian partisans on April 28, 1945, during the final days of World War II.<|end_search_result|>

think: Benito Mussolini was assassinated as part of World War II. So the Rome Protocols were signed by three Prime Ministers one of which was assassinated as part of World War II.
<|begin_answer|>\boxed{World War II}<|end_answer|>

Reflection: I searched one of the prime ministers involved in the signing, then attempted to answer right away. I should have searched each of the prime ministers, then looked up 'death' or 'assassination' on each of their pages in order to get more information before answering.
""",
"""
Previous Trial:
Question: Kam Heskin plays Paige Morgan in a 2004 film directed by who?

think: I need to search Kam Heskin and Paige Morgan, find the 2004 film they are in, then find the director of the film.
<|begin_search_query|>Kam Heskin<|end_search_query|>
<|begin_search_result|>Kam Erika Heskin (born May 8, 1973) is an American actress. She began her career playing Caitlin Deschanel on the NBC daytime soap opera Sunset Beach (1998–1999), before appearing in films Planet of the Apes (2001) and Catch Me If You Can (2002). Heskin went on in 2003 to play Elizabeth Bennet in an independent film Pride & Prejudice: A Latter-Day Comedy, Robin in Charmed (2004), and Paige Morgan in The Prince and Me film franchise (2006–2010).<|end_search_result|>

think: Kam Heskin plays Paige Morgan in The Prince and Me film franchise. I need to search The Prince and Me film franchise and find the director of the 2004 film.
<|begin_search_query|>The Prince and Me 2004 film director<|end_search_query|>
<|begin_search_result|>Could not find [The Prince and Me 2004 film]. Similar: ['The Prince & Me', 'The Prince & Me 2: The Royal Wedding', 'Kam Heskin', 'Prince of Darkness (film)', 'Prince of Persia: The Sands of Time (film)', 'Rob Knox', 'Alexander (2004 film)', 'Prince of Persia', 'Brooklynn Prince', 'Prince (musician)']<|end_search_result|>

think: I need to search The Prince & Me (2004 film) instead.
<|begin_search_query|>The Prince & Me 2004 film<|end_search_query|>
<|begin_search_result|>Could not find [The Prince & Me 2004 film]. Similar: ['The Prince & Me', 'The Prince & Me 2: The Royal Wedding', 'Prince of Darkness (film)', 'Prince of Persia: The Sands of Time (film)', 'Rob Knox', 'Alexander (2004 film)', 'Prince (musician)', 'Prince of Persia', 'Kam Heskin

"""]

SYSTEM_INSTRUCTION = """
You are a reasoning assistant solving HotpotQA questions. You have special tools:

1. Search Tool:
   - Format: <|begin_search_query|> your query here <|end_search_query|>
   - Use this to search for relevant information
   - You can make multiple searches (max 10 attempts)

2. Lookup Tool:
   - Format: <|begin_lookup_query|> specific query <|end_lookup_query|>
   - Use this to look up specific details from search results

3. Answer Submission:
   - Format: <|begin_answer|> your answer <|end_answer|>
   - Use this when you're confident about your answer

Guidelines:
- Break down complex questions into smaller parts
- Use natural language in your queries
- Explain your reasoning before each action
- Submit answers only when you're confident
- Format your final answer as \boxed{YOUR_ANSWER}
"""


human_instruction_template = """{instruction}You may take maximum of {max_steps} steps.
Here are some examples:"""

HUMAN_INSTRUCTION = HumanMessagePromptTemplate.from_template(human_instruction_template)

human_instruction_reflection_template = """Here are some examples:"""
HUMAN_REFLECTION_INSTRUCTION = HumanMessagePromptTemplate.from_template(human_instruction_reflection_template)

SYSTEM_CRITIQUE_EXISTING_RULES_INSTRUCTION = """You will be given two previous task trials in which you were given access to a Docstore API environment and a question to answer: one successful and one unsuccessful trial. You failed the trial either because you guessed the wrong answer with Finish[<answer>], or you used up your set number of reasoning steps."""
SYSTEM_CRITIQUE_ALL_SUCCESS_EXISTING_RULES_INSTRUCTION = """You will be given successful tasks trials in which you were given access to a Docstore API environment and a question to answer."""
SYSTEM_REFLECTION_INSTRUCTION = """You will be given a previous reasoning trial in which you were given access to a Docstore API environment and a question to answer. You were unsuccessful in answering the question either because you guessed the wrong answer with Finish[<answer>], or you used up your set number of reasoning steps. In a few sentences, Diagnose a possible reason for failure and devise a new, concise, high level plan that aims to mitigate the same failure. Use complete sentences."""


def LLM_PARSER(llm_output, step: int, ai_message: bool) -> Tuple[ChatMessage, str, Dict[str, Any]]:
    # First, try to extract the final answer if it exists
    boxed_answer_pattern = r'\\boxed{([^}]+)}'
    boxed_match = re.search(boxed_answer_pattern, llm_output)
    if boxed_match:
        answer = boxed_match.group(1)
        content = f"Action {step}: Finish[{answer}]"
        return (
            AIMessage(content=content) if ai_message else HumanMessage(content=content),
            'action',
            {'action': f"Finish[{answer}]"}
        )

    # Try to extract search queries
    search_pattern = r'<\|begin_search_query\|>(.*?)<\|end_search_query\|>'
    search_match = re.search(search_pattern, llm_output, re.DOTALL)
    if search_match:
        query = search_match.group(1).strip()
        content = f"Action {step}: Search[{query}]"
        return (
            AIMessage(content=content) if ai_message else HumanMessage(content=content),
            'action',
            {'action': f"Search[{query}]"}
        )

    # Try to extract lookup queries
    lookup_pattern = r'<\|begin_lookup_query\|>(.*?)<\|end_lookup_query\|>'
    lookup_match = re.search(lookup_pattern, llm_output, re.DOTALL)
    if lookup_match:
        query = lookup_match.group(1).strip()
        content = f"Action {step}: Lookup[{query}]"
        return (
            AIMessage(content=content) if ai_message else HumanMessage(content=content),
            'action',
            {'action': f"Lookup[{query}]"}
        )

    # If no action found, treat as thought
    # Extract thought from <think> tags if present
    think_pattern = r'<think>(.*?)</think>'
    think_match = re.search(think_pattern, llm_output, re.DOTALL)
    if think_match:
        thought = think_match.group(1).strip()
        content = f"Thought {step}: {thought}"
    else:
        # If no <think> tags, use the whole output as thought
        content = f"Thought {step}: {llm_output.rstrip(':')}"
    
    return (
        AIMessage(content=content) if ai_message else HumanMessage(content=content),
        'thought',
        {}
    )


def OBSERVATION_FORMATTER(observation: str, step: int, *args, **kwargs) -> Tuple[ChatMessage, str]:
    return HumanMessage(content=f"Observation {step}: " + observation.rstrip(':')), 'append'

def STEP_IDENTIFIER(line: str) -> str:
    line = line.strip()
    pattern = re.compile(r'^(?i)action(?:\s+(\d+))?:')
    match = pattern.match(line)
    if match:
        return 'action'
    pattern = re.compile(r'^(?i)observation(?:\s+(\d+))?:')
    match = pattern.match(line)
    if match:
        return 'observation'
    return 'think'

def CYCLER(lines: str) -> List[str]:
    new_lines = []
    scratch_pad = ''
    for line in lines.split('\n'):

        # line is action
        pattern = re.compile(r'^(?i)action(?:\s+(\d+))?:')
        match = pattern.match(line)
        if match:
            if scratch_pad != '':
                new_lines.append(scratch_pad.strip())
                scratch_pad = ''
            new_lines.append(line)
            continue

        # line is think
        pattern = re.compile(r'^(?i)think(?:\s+(\d+))?:')
        match = pattern.match(line)
        if match:
            if scratch_pad != '':
                new_lines.append(scratch_pad.strip())
                scratch_pad = ''
            new_lines.append(line)
            continue

        # step is observation
        scratch_pad += line + '\n'

    # the rest of the scratch pad
    if scratch_pad != '':
        new_lines.append(scratch_pad.strip())
    return new_lines

REFLECTION_PREFIX = '\nReflection:'
def PREVIOUS_TRIALS_FORMATTER(reflections: List[str], include_prefix: bool = True) -> str:
    if reflections == []:
        return ''
    if include_prefix:
        memory_prefix = "You have attempted to solve the task before but failed. The following reflection(s) give a plan to avoid failing the task in the same way you did previously. Use them to improve your strategy of solving the task successfully."
    else:
        memory_prefix = ''
    memory_prefix += '\nReflections:'
    for reflection in reflections:
        memory_prefix += f"\n- {reflection.strip()}"
    return memory_prefix



def STEP_STRIPPER(step: str, step_type: str):
    """
    Strip step prefixes and format the content appropriately.
    
    Args:
        step (str): The step content to be stripped
        step_type (str): Type of step ('observation', 'action', or 'think')
    
    Returns:
        str: Stripped and formatted step content
    """
    # First remove the step number prefix
    step = re.sub(r'^(?i)(observation|action|think)(?:\s+(\d+))?:', r'\1:', step)
    
    if step_type == 'observation':
        # Handle search and lookup results
        if '<|begin_search_result|>' in step:
            # Extract content between tags
            content = re.search(r'<\|begin_search_result\|>(.*?)<\|end_search_result\|>', step, re.DOTALL)
            if content:
                return f"Observation: {content.group(1).strip()}"
        elif '<|begin_lookup_result|>' in step:
            # Extract content between tags
            content = re.search(r'<\|begin_lookup_result\|>(.*?)<\|end_lookup_result\|>', step, re.DOTALL)
            if content:
                return f"Observation: {content.group(1).strip()}"
        return f"Observation: {step.replace('Observation:', '').strip()}"
        
    elif step_type == 'action':
        # Handle search, lookup, and finish actions
        if '<|begin_search_query|>' in step:
            content = re.search(r'<\|begin_search_query\|>(.*?)<\|end_search_query\|>', step, re.DOTALL)
            if content:
                return f"Action: Search[{content.group(1).strip()}]"
        elif '<|begin_lookup_query|>' in step:
            content = re.search(r'<\|begin_lookup_query\|>(.*?)<\|end_lookup_query\|>', step, re.DOTALL)
            if content:
                return f"Action: Lookup[{content.group(1).strip()}]"
        elif '<|begin_answer|>' in step:
            content = re.search(r'<\|begin_answer\|>(.*?)<\|end_answer\|>', step, re.DOTALL)
            if content:
                return f"Action: Finish[{content.group(1).strip()}]"
        return f"Action: {step.replace('Action:', '').strip()}"
        
    elif step_type == 'think':
        # Clean up think content
        think = step.replace('think:', '').strip()
        # Remove any remaining tags
        think = re.sub(r'<\|.*?\|>', '', think)
        return f"think: {think}"
        
    return step


from typing import Callable, List
import time
import ollama
from langchain.schema import ChatMessage

class OllamaWrapper:
    def __init__(self, host: str = "http://192.168.4.168:11434", model: str = "qwq:latest"):
        self.client = ollama.Client(host=host)
        self.model = model

    def __call__(self, messages: List[ChatMessage], stop: List[str] = [], replace_newline: bool = True) -> str:
        # Convert messages to Ollama format
        ollama_messages = []
        for msg in messages:
            role = msg.type
            content = msg.content
            if role == "human":
                ollama_messages.append({"role": "user", "content": content})
            elif role == "ai":
                ollama_messages.append({"role": "assistant", "content": content})
            else:
                ollama_messages.append({"role": "system", "content": content})

        # Make request to Ollama
        for i in range(6):  # Retry logic
            try:
                print("input_messages", ollama_messages)
                response = self.client.chat(
                    model=self.model,
                    messages=ollama_messages,
                    stream=False
                )
                output = response.message.content.strip()
                print("output", output)
                break
            except Exception as e:
                print(f'\nRetrying {i}... Error: {str(e)}')
                time.sleep(1)
        else:
            raise RuntimeError('Failed to generate response from Ollama')

        if replace_newline:
            output = output.replace('\n', '')
        return output

class GPTWrapper:
    def __init__(self, llm_name: str, openai_api_key: str, long_ver: bool):
        self.model_name = 'qwq:latest'
        if long_ver:
            llm_name = 'qwq:latest'
        
        # Initialize the Ollama wrapper
        self.llm = OllamaWrapper(
            host="http://192.168.4.168:11434",
            model=self.model_name
        )

    def __call__(self, messages: List[ChatMessage], stop: List[str] = [], replace_newline: bool = True) -> str:
        kwargs = {}
        if stop != []:
            kwargs['stop'] = stop
        for i in range(6):
            try:
                print("this is llm", self.llm)
                print("input_message", messages)
                print("\n", "\n")
                output = self.llm(messages, **kwargs)
                print("outputttttttttttt", output)
                break
            except Exception as e:
                print(f'\nRetrying {i}...')
                time.sleep(1)
        else:
            raise RuntimeError('Failed to generate response')

        if replace_newline:
            output = output.replace('\n', '')
        return output

def LLM_CLS(llm_name: str, openai_api_key: str, long_ver: bool) -> Callable:
    if 'qwq:latest' in llm_name:
        return GPTWrapper(llm_name, openai_api_key, long_ver)
    else:
        raise ValueError(f"Unknown LLM model name: {llm_name}")















generate_endpoint = f"http://192.168.4.162:11434/api/chat"
headers = {'Content-Type': 'application/json'}
 
payload = {
"model": "qwq:latest",
"messages": msg_history,
"stream": False,
"options": {"temperature": 1.0}}
response = requests.post(generate_endpoint, headers=headers, json=payload).json()
content = response.get('message', {}).get('content', '')


from typing import Callable, List
import time
from langchain.chat_models import ChatOpenAI
from langchain_community.chat_models import ChatOllama 
# from langchain_openai import ChatOpenAI
from langchain.schema import ChatMessage
import openai



class GPTWrapper:
    def __init__(self, llm_name: str, openai_api_key: str, long_ver: bool):
        self.model_name = 'qwq:latest'
        if long_ver:
            llm_name = 'qwq:latest'
        # self.llm = ChatOpenAI(
        #     model=llm_name,
        #     temperature=0.0,
        #     openai_api_key="ollama",
        #     base_url="http://192.168.4.168:11434"
        # )
        self.llm = ChatOllama(
            model=self.model_name,
            base_url="http://192.168.4.162:11434",  # your Ollama instance
            # temperature=0.5 
        )
        

    def __call__(self, messages: List[ChatMessage], stop: List[str] = [], replace_newline: bool = True) -> str:
        kwargs = {}
        if stop != []:
            kwargs['stop'] = stop
        for i in range(6):
            try:
                print("this is llm", self.llm)
                print("input_message",messages)
                print("\n","\n")
                output = self.llm(messages, **kwargs).content#.strip('\n').strip()
                print("outputttttttttttt",output)
                end()
                break

            except Exception as e:
                print(f'\nRetrying {i}...')
                time.sleep(1)
        else:
            raise RuntimeError('Failed to generate response')

        if replace_newline:
            output = output.replace('\n', '')
        return output

def LLM_CLS(llm_name: str, openai_api_key: str, long_ver: bool) -> Callable:
    if 'qwq:latest' in llm_name:
        return GPTWrapper(llm_name, openai_api_key, long_ver)
    else:
        raise ValueError(f"Unknown LLM model name: {llm_name}")



















import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
import random
import joblib
import numpy as np
import pandas as pd

def clean_for_json(obj):
    """Recursively convert numpy types to native Python types."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.generic):
        return obj.item()
    elif isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(i) for i in obj]
    else:
        return obj

def load_hotpotqa_data(file_path: str) -> List[Dict[str, Any]]:
    """Load HotpotQA data from joblib file."""
    # Load the joblib file into a pandas DataFrame
    df = joblib.load(file_path)
    
    # Convert to list of dictionaries with cleaned numpy types
    data = []
    for _, row in df.iterrows():
        # Clean numpy types in context and supporting_facts
        context = clean_for_json(row["context"])
        supporting_facts = clean_for_json(row["supporting_facts"])
        
        data.append({
            "_id": row["id"],
            "type": row["type"],
            "level": row["level"],
            "question": row["question"],
            "answer": row["answer"],
            "context": context,
            "supporting_facts": supporting_facts
        })
    
    return data

def convert_to_knowself_format(example: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a HotpotQA example to KnowSelf format."""
    # Extract relevant information
    question = example['question']
    answer = example['answer']
    supporting_facts = example['supporting_facts']
    context = example['context']
    
    # Create the input text
    input_text = f"Question: {question}\n\nContext:\n"
    for title, sentences in context:
        input_text += f"{title}:\n"
        for sent in sentences:
            input_text += f"{sent}\n"
    
    # Create the output text with special tokens
    output_text = f"Let me analyze this step by step:\n"
    
    # Add reasoning steps
    for i, (title, sent_id) in enumerate(supporting_facts, 1):
        sent = next(sent for t, sents in context if t == title for sent in sents if sent_id == sents.index(sent))
        output_text += f"Step {i}: {sent}\n"
    
    # Add final answer
    output_text += f"\nFinal Answer: {answer}"
    
    return {
        "input": input_text,
        "output": output_text,
        "metadata": {
            "question_id": example['_id'],
            "type": example['type'],
            "level": example['level']
        }
    }

def main():
    parser = argparse.ArgumentParser(description='Preprocess HotpotQA dataset for KnowSelf')
    parser.add_argument('--input_file', type=str, required=True, help='Path to HotpotQA joblib file')
    parser.add_argument('--output_file', type=str, required=True, help='Path to save processed data')
    parser.add_argument('--train_ratio', type=float, default=0.9, help='Ratio of data to use for training')
    args = parser.parse_args()
    
    # Load data
    data = load_hotpotqa_data(args.input_file)
    
    # Convert to KnowSelf format
    processed_data = [convert_to_knowself_format(example) for example in data]
    
    # Split into train/val
    random.shuffle(processed_data)
    split_idx = int(len(processed_data) * args.train_ratio)
    train_data = processed_data[:split_idx]
    val_data = processed_data[split_idx:]
    
    # Save processed data
    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(train_data, f, indent=2)
    
    val_path = output_path.parent / f"val_{output_path.name}"
    with open(val_path, 'w', encoding='utf-8') as f:
        json.dump(val_data, f, indent=2)
    
    print(f"Processed {len(processed_data)} examples")
    print(f"Saved {len(train_data)} training examples to {output_path}")
    print(f"Saved {len(val_data)} validation examples to {val_path}")

if __name__ == '__main__':
    main()

SYSTEM_INSTRUCTION = """
You are a reasoning assistant solving HotpotQA questions. You have special tools:

1. Search Tool:
   - Format: <|begin_search_query|> your query here <|end_search_query|>
   - Use this to search for relevant information
   - You can make multiple searches (max 10 attempts)

2. Lookup Tool:
   - Format: <|begin_lookup_query|> specific query <|end_lookup_query|>
   - Use this to look up specific details from search results

3. Answer Submission:
   - Format: <|begin_answer|> your answer <|end_answer|>
   - Use this when you're confident about your answer

Guidelines:
- Break down complex questions into smaller parts
- Use natural language in your queries
- Explain your reasoning before each action
- Submit answers only when you're confident
- Format your final answer as \boxed{YOUR_ANSWER}
"""



in prompts def LLM_PARSER(llm_output, step: int, ai_message: bool) -> Tuple[ChatMessage, str, Dict[str, Any]]:
    # Search query pattern
    search_pattern = r'<\|begin_search_query\|>(.*?)<\|end_search_query\|>'
    # Lookup query pattern
    lookup_pattern = r'<\|begin_lookup_query\|>(.*?)<\|end_lookup_query\|>'
    # Answer pattern
    answer_pattern = r'<\|begin_answer\|>(.*?)<\|end_answer\|>'

    # Check for search query
    search_match = re.search(search_pattern, llm_output, re.DOTALL)
    if search_match:
        query = search_match.group(1).strip()
        content = f"Action {step}: Search[{query}]"
        return (
            AIMessage(content=content) if ai_message else HumanMessage(content=content),
            'action',
            {'action': f"Search[{query}]"}
        )

    # Check for lookup query
    lookup_match = re.search(lookup_pattern, llm_output, re.DOTALL)
    if lookup_match:
        query = lookup_match.group(1).strip()
        content = f"Action {step}: Lookup[{query}]"
        return (
            AIMessage(content=content) if ai_message else HumanMessage(content=content),
            'action',
            {'action': f"Lookup[{query}]"}
        )

    # Check for answer
    answer_match = re.search(answer_pattern, llm_output, re.DOTALL)
    if answer_match:
        answer = answer_match.group(1).strip()
        content = f"Action {step}: Finish[{answer}]"
        return (
            AIMessage(content=content) if ai_message else HumanMessage(content=content),
            'action',
            {'action': f"Finish[{answer}]"}
        )

    # If no action found, treat as thought
    thought_pattern = r'(?i)thought\s*(?:\d+|)\s*(?::|)\s*(.*)'
    match = re.match(thought_pattern, llm_output)
    if match:
        thought = match.group(1)
        content = f"Thought {step}: {thought.rstrip(':')}"
    else:
        content = f"Thought {step}: {llm_output.rstrip(':')}"
    return (
        AIMessage(content=content) if ai_message else HumanMessage(content=content),
        'thought',
        {}
    )


reflectionfewshot
REFLECTION_FEWSHOTS = [
"""
Previous Trial:
Question: The Rome Protocols were signed by three Prime Ministers one of which was assassinated as part of what?

Thought: I need to search Rome Protocols, find the three Prime Ministers, then find what they were assassinated as part of.
<|begin_search_query|>Rome Protocols<|end_search_query|>
<|begin_search_result|>The Rome Protocols were a series of three international agreements concluded in Rome on 17 March 1934 between the governments of Austria, Hungary and Italy. They were signed by Italian Prime Minister Benito Mussolini, Austrian Chancellor Engelbert Dollfuss and Hungarian Prime Minister Gyula Gömbös.<|end_search_result|>

Thought: The three Prime Ministers were Benito Mussolini, Engelbert Dollfuss, and Gyula Gömbös. I need to search Benito Mussolini and find what he was assassinated as part of.
<|begin_search_query|>Benito Mussolini assassination<|end_search_query|>
<|begin_search_result|>Benito Mussolini was executed by Italian partisans on April 28, 1945, during the final days of World War II.<|end_search_result|>

Thought: Benito Mussolini was assassinated as part of World War II. So the Rome Protocols were signed by three Prime Ministers one of which was assassinated as part of World War II.
<|begin_answer|>\boxed{World War II}<|end_answer|>

Reflection: I searched one of the prime ministers involved in the signing, then attempted to answer right away. I should have searched each of the prime ministers, then looked up 'death' or 'assassination' on each of their pages in order to get more information before answering.
""",
"""
Previous Trial:
Question: Kam Heskin plays Paige Morgan in a 2004 film directed by who?

Thought: I need to search Kam Heskin and Paige Morgan, find the 2004 film they are in, then find the director of the film.
<|begin_search_query|>Kam Heskin<|end_search_query|>
<|begin_search_result|>Kam Erika Heskin (born May 8, 1973) is an American actress. She began her career playing Caitlin Deschanel on the NBC daytime soap opera Sunset Beach (1998–1999), before appearing in films Planet of the Apes (2001) and Catch Me If You Can (2002). Heskin went on in 2003 to play Elizabeth Bennet in an independent film Pride & Prejudice: A Latter-Day Comedy, Robin in Charmed (2004), and Paige Morgan in The Prince and Me film franchise (2006–2010).<|end_search_result|>

Thought: Kam Heskin plays Paige Morgan in The Prince and Me film franchise. I need to search The Prince and Me film franchise and find the director of the 2004 film.
<|begin_search_query|>The Prince and Me 2004 film director<|end_search_query|>
<|begin_search_result|>Could not find [The Prince and Me 2004 film]. Similar: ['The Prince & Me', 'The Prince & Me 2: The Royal Wedding', 'Kam Heskin', 'Prince of Darkness (film)', 'Prince of Persia: The Sands of Time (film)', 'Rob Knox', 'Alexander (2004 film)', 'Prince of Persia', 'Brooklynn Prince', 'Prince (musician)']<|end_search_result|>

Thought: I need to search The Prince & Me (2004 film) instead.
<|begin_search_query|>The Prince & Me 2004 film<|end_search_query|>
<|begin_search_result|>Could not find [The Prince & Me 2004 film]. Similar: ['The Prince & Me', 'The Prince & Me 2: The Royal Wedding', 'Prince of Darkness (film)', 'Prince of Persia: The Sands of Time (film)', 'Rob Knox', 'Alexander (2004 film)', 'Prince (musician)', 'Prince of Persia', 'Kam Heskin

in envs


class QAEnv(BaseEnv):
    def __init__(self,
                 question: str,
                 key: str,
                 max_steps: int = 10,  # Increased max steps for reasoning models
                 explorer: DocstoreExplorer = DocstoreExplorer(Wikipedia())):

        self.question = question
        self.key = key
        self.max_steps = max_steps
        self.explorer = explorer
        self.task = """multi-hop QA. The agent was given access to a Docstore API environment and a question to answer. The agent can search for pages related to the question, lookup keywords in the pages, and finish with an answer."""
        self.env_name = 'hotpotqa'
        self.reset()

    def step(self, action: str) -> Tuple[str, bool, bool, bool, bool]:
        action_type, argument = parse_action(action)

        if action_type == 'Finish':
            self.answer = argument
            if self.success_fn():
                observation = 'Answer is CORRECT'
            else: 
                observation = f'Answer is INCORRECT'
            self.terminated = True
        elif action_type == 'Search':
            try:
                observation = self.explorer.search(argument).strip('\n').strip()
                # Format observation for reasoning model
                observation = f"<|begin_search_result|>{observation}<|end_search_result|>"
            except Exception as e:
                observation = f"<|begin_search_result|>Error: {str(e)}<|end_search_result|>"
                time.sleep(5)
        elif action_type == 'Lookup':
            try:
                observation = self.explorer.lookup(argument).strip('\n').strip()
                # Format observation for reasoning model
                observation = f"<|begin_lookup_result|>{observation}<|end_lookup_result|>"
            except ValueError:
                observation = f"<|begin_lookup_result|>The last page Searched was not found, so you cannot Lookup a keyword in it. Please try one of the similar pages given.<|end_lookup_result|>"
        else:
            observation = 'Invalid Action. Valid Actions are Lookup[<topic>] Search[<topic>] and Finish[<answer>].'

        self.curr_step += 1
        self.reward = self.success_fn()
        self.terminated = self.is_terminated()
        self.truncated = self.is_truncated()

        return observation, self.reward, self.terminated, self.truncated, self.curr_step


in utils

def format_reasoning_response(response: str) -> str:
    """Format the response from a reasoning model to match the environment's expected format."""
    # Add thought prefix if not present
    if not response.startswith('Thought'):
        response = f"Thought: {response}"
    
    # Ensure proper formatting for actions
    response = response.replace('<|begin_search_query|>', 'Search[')
    response = response.replace('<|end_search_query|>', ']')
    response = response.replace('<|begin_lookup_query|>', 'Lookup[')
    response = response.replace('<|end_lookup_query|>', ']')
    response = response.replace('<|begin_answer|>', 'Finish[')
    response = response.replace('<|end_answer|>', ']')
    
    return response


fewshot


FEWSHOTS = ["""
Question: What is the elevation range for the area that the eastern sector of the Colorado orogeny extends into?
Thought: I need to search Colorado orogeny, find the area that the eastern sector of the Colorado orogeny extends into, then find the elevation range of the area.
<|begin_search_query|>Colorado orogeny<|end_search_query|>
<|begin_search_result|>The Colorado orogeny was an episode of mountain building (an orogeny) in Colorado and surrounding areas.<|end_search_result|>
Thought: It does not mention the eastern sector. So I need to look up eastern sector.
<|begin_lookup_query|>eastern sector<|end_lookup_query|>
<|begin_lookup_result|>The eastern sector extends into the High Plains and is called the Central Plains orogeny.<|end_lookup_result|>
Thought: The eastern sector of Colorado orogeny extends into the High Plains. So I need to search High Plains and find its elevation range.
<|begin_search_query|>High Plains elevation range<|end_search_query|>
<|begin_search_result|>The High Plains are a subregion of the Great Plains. From east to west, the High Plains rise in elevation from around 1,800 to 7,000 ft (550 to 2,130 m).<|end_search_result|>
Thought: High Plains rise in elevation from around 1,800 to 7,000 ft, so the answer is 1,800 to 7,000 ft.
<|begin_answer|>1,800 to 7,000 ft<|end_answer|>
"""]



in prompt.py
def STEP_STRIPPER(step: str, step_type: str):
    """
    Strip step prefixes and format the content appropriately.
    
    Args:
        step (str): The step content to be stripped
        step_type (str): Type of step ('observation', 'action', or 'thought')
    
    Returns:
        str: Stripped and formatted step content
    """
    # First remove the step number prefix
    step = re.sub(r'^(?i)(observation|action|thought)(?:\s+(\d+))?:', r'\1:', step)
    
    if step_type == 'observation':
        # Handle search and lookup results
        if '<|begin_search_result|>' in step:
            # Extract content between tags
            content = re.search(r'<\|begin_search_result\|>(.*?)<\|end_search_result\|>', step, re.DOTALL)
            if content:
                return f"Observation: {content.group(1).strip()}"
        elif '<|begin_lookup_result|>' in step:
            # Extract content between tags
            content = re.search(r'<\|begin_lookup_result\|>(.*?)<\|end_lookup_result\|>', step, re.DOTALL)
            if content:
                return f"Observation: {content.group(1).strip()}"
        return f"Observation: {step.replace('Observation:', '').strip()}"
        
    elif step_type == 'action':
        # Handle search, lookup, and finish actions
        if '<|begin_search_query|>' in step:
            content = re.search(r'<\|begin_search_query\|>(.*?)<\|end_search_query\|>', step, re.DOTALL)
            if content:
                return f"Action: Search[{content.group(1).strip()}]"
        elif '<|begin_lookup_query|>' in step:
            content = re.search(r'<\|begin_lookup_query\|>(.*?)<\|end_lookup_query\|>', step, re.DOTALL)
            if content:
                return f"Action: Lookup[{content.group(1).strip()}]"
        elif '<|begin_answer|>' in step:
            content = re.search(r'<\|begin_answer\|>(.*?)<\|end_answer\|>', step, re.DOTALL)
            if content:
                return f"Action: Finish[{content.group(1).strip()}]"
        return f"Action: {step.replace('Action:', '').strip()}"
        
    elif step_type == 'thought':
        # Clean up thought content
        thought = step.replace('Thought:', '').strip()
        # Remove any remaining tags
        thought = re.sub(r'<\|.*?\|>', '', thought)
        return f"Thought: {thought}"
        
    return step


# run_search_o1_wiki.py
import os
import json
import time
import re
from tqdm import tqdm
import numpy as np
import torch
import string
from typing import Optional, Tuple, List, Dict
import argparse

from transformers import AutoTokenizer
from vllm import LLM, SamplingParams

from wikipedia_search import (
    wikipedia_search, 
    extract_relevant_info
)
from evaluate import (
    run_evaluation, 
    extract_answer
)
from prompts import (
    get_gpqa_search_o1_instruction, 
    get_math_search_o1_instruction, 
    get_code_search_o1_instruction, 
    get_singleqa_search_o1_instruction, 
    get_multiqa_search_o1_instruction, 
    get_webpage_to_reasonchain_instruction,
    get_task_instruction_openqa, 
    get_task_instruction_math, 
    get_task_instruction_multi_choice, 
    get_task_instruction_code, 
)

# Define special tokens
BEGIN_SEARCH_QUERY = "<|begin_search_query|>"
END_SEARCH_QUERY = "<|end_search_query|>"
BEGIN_SEARCH_RESULT = "<|begin_search_result|>"
END_SEARCH_RESULT = "<|end_search_result|>"

def parse_args():
    parser = argparse.ArgumentParser(description="Run Search O1 for various datasets and models.")

    # Dataset and split configuration
    parser.add_argument(
        '--dataset_name',
        type=str,
        required=True,
        choices=['gpqa', 'math500', 'aime', 'amc', 'livecode', 'nq', 'triviaqa', 'hotpotqa', '2wiki', 'musique', 'bamboogle'],
        help="Name of the dataset to use."
    )

    parser.add_argument(
        '--split',
        type=str,
        required=True,
        choices=['test', 'diamond', 'main', 'extended'],
        help="Dataset split to use."
    )

    parser.add_argument(
        '--subset_num',
        type=int,
        default=-1,
        help="Number of examples to process. Defaults to all if not specified."
    )

    # Search and document retrieval configuration
    parser.add_argument(
        '--max_search_limit',
        type=int,
        default=10,
        help="Maximum number of searches per question."
    )

    parser.add_argument(
        '--max_turn',
        type=int,
        default=15,
        help="Maximum number of turns."
    )

    parser.add_argument(
        '--top_k',
        type=int,
        default=10,
        help="Maximum number of search documents to return."
    )

    parser.add_argument(
        '--max_doc_len',
        type=int,
        default=3000,
        help="Maximum length of each searched document."
    )

    # Model configuration
    parser.add_argument(
        '--model_path',
        type=str,
        required=True,
        help="Path to the pre-trained model."
    )

    # Sampling parameters
    parser.add_argument(
        '--temperature',
        type=float,
        default=0.7,
        help="Sampling temperature."
    )

    parser.add_argument(
        '--top_p',
        type=float,
        default=0.8,
        help="Top-p sampling parameter."
    )

    parser.add_argument(
        '--top_k_sampling',
        type=int,
        default=20,
        help="Top-k sampling parameter."
    )

    parser.add_argument(
        '--repetition_penalty',
        type=float,
        default=None,
        help="Repetition penalty. If not set, defaults based on the model."
    )

    parser.add_argument(
        '--max_tokens',
        type=int,
        default=32768,
        help="Maximum number of tokens to generate. If not set, defaults based on the model and dataset."
    )

    return parser.parse_args()
import sys, os, os.path
os.environ['http_proxy'] = "http://vproxy.toshiba-tsip.com:8080"
os.environ['https_proxy'] = "http://vproxy.toshiba-tsip.com:8080"
def main():
    args = parse_args()

    # Extract arguments
    dataset_name = args.dataset_name
    split = args.split
    subset_num = args.subset_num
    MAX_SEARCH_LIMIT = args.max_search_limit
    MAX_TURN = args.max_turn
    top_k = args.top_k
    max_doc_len = args.max_doc_len
    model_path = args.model_path
    temperature = args.temperature
    top_p = args.top_p
    top_k_sampling = args.top_k_sampling
    repetition_penalty = args.repetition_penalty
    max_tokens = args.max_tokens

    # Set default repetition_penalty if not provided
    if repetition_penalty is None:
        repetition_penalty = 1.05 if 'qwq' in model_path.lower() else 1.0

    # Adjust parameters based on dataset
    if dataset_name in ['nq', 'triviaqa', 'hotpotqa', 'musique', 'bamboogle', '2wiki']:
        MAX_SEARCH_LIMIT = 5
        if dataset_name in ['hotpotqa', 'musique', 'bamboogle', '2wiki']:
            MAX_SEARCH_LIMIT = 10
            MAX_TURN = 15
        top_k = 10
        max_doc_len = 3000

    # Data paths based on dataset
    if dataset_name == 'livecode':
        data_path = f'./data/LiveCodeBench/{split}.json'
    elif dataset_name in ['math500', 'gpqa', 'aime', 'amc']:
        data_path = f'./data/{dataset_name.upper()}/{split}.json'
    else:
        data_path = f'./data/QA_Datasets/{dataset_name}.json'

    print('-----------------------')
    print(f'Using {dataset_name} {split} set.')
    print('-----------------------')

    # ---------------------- Caching Mechanism ----------------------
    # Define cache directories and file paths
    cache_dir = './cache'
    search_cache_path = os.path.join(cache_dir, 'search_cache.json')

    # Ensure cache directory exists
    os.makedirs(cache_dir, exist_ok=True)

    # Load existing caches or initialize empty dictionaries
    if os.path.exists(search_cache_path):
        with open(search_cache_path, 'r', encoding='utf-8') as f:
            search_cache = json.load(f)
    else:
        search_cache = {}

    # Function to save caches
    def save_caches():
        with open(search_cache_path, 'w', encoding='utf-8') as f:
            json.dump(search_cache, f, ensure_ascii=False, indent=2)

    cache_dir1 = "/home/data/abhishek/Hugging_face_Dataset/hub"
    # ---------------------- Model Loading ----------------------
    tokenizer = AutoTokenizer.from_pretrained(model_path, cache_dir=cache_dir1,trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = 'left'

    print("tokenization done")
    # Initialize the LLM
    llm = LLM(
        model=model_path,
        tensor_parallel_size=torch.cuda.device_count(),
        gpu_memory_utilization=0.95,
        # cache_dir=cache_dir1,
        trust_remote_code=True
    )

    # Define output directory based on model and dataset
    if 'qwq' in model_path.lower():
        if dataset_name in ['math500', 'gpqa', 'aime', 'amc', 'livecode']:
            output_dir = f'./outputs/{dataset_name}.qwq.search_o1'
            if dataset_name == 'gpqa' and (MAX_SEARCH_LIMIT != 5 or top_k != 10):
                output_dir = f'./outputs/runs.analysis/{dataset_name}.qwq.search_o1.{MAX_SEARCH_LIMIT}.{top_k}'
        else:
            output_dir = f'./outputs/runs.qa/{dataset_name}.qwq.search_o1'
    else:
        model_short_name = model_path.split('/')[-1].lower().replace('-instruct', '')
        output_dir = f'./outputs/runs.baselines/{dataset_name}.{model_short_name}.search_o1'
    os.makedirs(output_dir, exist_ok=True)

    # ---------------------- Data Loading ----------------------
    with open(data_path, 'r', encoding='utf-8') as json_file:
        filtered_data = json.load(json_file)

    # ---------------------- Batch Generation Function ----------------------
    def generate_webpage_to_reasonchain_batch(
        original_questions: List[str],
        prev_reasonings: List[str],
        search_queries: List[str],
        documents: List[str],
        dataset_name: str,
        batch_output_records: List[Dict],
        max_tokens: int = 32768,
    ) -> List[str]:
        user_prompts = [
            get_webpage_to_reasonchain_instruction(r, sq, doc)
            for r, sq, doc in zip(prev_reasonings, search_queries, documents)
        ]

        prompts = [{"role": "user", "content": up} for up in user_prompts]
        prompts = [tokenizer.apply_chat_template([p], tokenize=False, add_generation_prompt=True) for p in prompts]

        output = llm.generate(
            prompts,
            sampling_params=SamplingParams(
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=0.8,
                top_k=20,
                repetition_penalty=1.05,
            )
        )

        raw_outputs = [out.outputs[0].text for out in output]
        extracted_infos = [extract_answer(raw, mode='infogen') for raw in raw_outputs]

        for i, (p, r, e) in enumerate(zip(prompts, raw_outputs, extracted_infos)):
            batch_output_records.append({
                'prompt': p,
                'raw_output': r,
                'extracted_info': e
            })

        return extracted_infos

    # ---------------------- Preparation of Input Prompts ----------------------
    input_list = []
    for item in filtered_data:
        question = item['question']

        if dataset_name in ['nq', 'triviaqa', 'hotpotqa', 'musique', 'bamboogle', '2wiki']:
            if dataset_name in ['nq', 'triviaqa']:
                instruction = get_singleqa_search_o1_instruction(MAX_SEARCH_LIMIT)
                # print(instruction)
            elif dataset_name in ['hotpotqa', 'musique', 'bamboogle', '2wiki']:
                instruction = get_multiqa_search_o1_instruction(MAX_SEARCH_LIMIT)
                # print("instructions:",instruction)

            if 'qwq' in model_path.lower():
                user_prompt = get_task_instruction_openqa(question, model_name='qwq')
            else:
                user_prompt = get_task_instruction_openqa(question)
            # print("/n")
            # print("user_prompt",user_prompt)
            # end()

        elif dataset_name in ['math500', 'aime', 'amc']:
            instruction = get_math_search_o1_instruction(MAX_SEARCH_LIMIT)
            if 'qwq' in model_path.lower():
                user_prompt = get_task_instruction_math(question, model_name='qwq')
            else:
                user_prompt = get_task_instruction_math(question)

        elif dataset_name == 'gpqa':
            instruction = get_gpqa_search_o1_instruction(MAX_SEARCH_LIMIT)
            if 'qwq' in model_path.lower():
                user_prompt = get_task_instruction_multi_choice(question, model_name='qwq')
            elif 'llama' in model_path.lower():
                user_prompt = get_task_instruction_multi_choice(question, model_name='llama')
            else:
                user_prompt = get_task_instruction_multi_choice(question)

        elif dataset_name == 'livecode':
            instruction = get_code_search_o1_instruction(MAX_SEARCH_LIMIT)
            question_title = item.get('question_title', '')
            if 'qwq' in model_path.lower():
                user_prompt = get_task_instruction_code(question, question_title=question_title, model_name='qwq')
            else:
                user_prompt = get_task_instruction_code(question)
        else:
            user_prompt = ""

        prompt = [{"role": "user", "content": instruction + user_prompt}]
        prompt = tokenizer.apply_chat_template(prompt, tokenize=False, add_generation_prompt=True)
        input_list.append(prompt)

    if subset_num != -1:
        input_list = input_list[:subset_num]
        filtered_data = filtered_data[:subset_num]

    # Initialize active sequences
    active_sequences = [{
        'item': item,
        'prompt': prompt,
        'output': '',
        'finished': False,
        'history': [],
        'search_count': 0,
        'executed_search_queries': set(),
    } for item, prompt in zip(filtered_data, input_list)]

    # ---------------------- Set Max Tokens ----------------------
    if 'qwq' in model_path.lower():
        if dataset_name in ['aime', 'amc', 'livecode']:
            max_tokens = 32768
        else:
            max_tokens = 20480
    else:
        max_tokens = 8192

    # ---------------------- Generation Function ----------------------
    def run_generation(sequences: List[Dict], max_tokens: int) -> List:
        prompts = [s['prompt'] for s in sequences]
        sampling_params = SamplingParams(
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k_sampling,
            repetition_penalty=repetition_penalty,
            stop=[END_SEARCH_QUERY, tokenizer.eos_token],
            include_stop_str_in_output=True,
        )
        output_list = llm.generate(prompts, sampling_params=sampling_params)
        print("output_list",output_list,"/n")
        return output_list

    # Function to extract text between two tags
    def extract_between(text: str, start_tag: str, end_tag: str) -> Optional[str]:
        pattern = re.escape(start_tag) + r"(.*?)" + re.escape(end_tag)
        matches = re.findall(pattern, text, flags=re.DOTALL)
        if matches:
            return matches[-1].strip()
        return None

    def replace_recent_steps(origin_str, replace_str):
        def parse_steps(text):
            step_pattern = re.compile(r"Step\s+(\d+):\s*")
            steps = {}
            current_step_num = None
            current_content = []

            for line in text.splitlines():
                step_match = step_pattern.match(line)
                if step_match:
                    if current_step_num is not None:
                        steps[current_step_num] = "\n".join(current_content).strip()
                    current_step_num = int(step_match.group(1))
                    content = line[step_match.end():].strip()
                    current_content = [content] if content else []
                else:
                    if current_step_num is not None:
                        current_content.append(line)
            
            if current_step_num is not None:
                steps[current_step_num] = "\n".join(current_content).strip()
            
            return steps

        origin_steps = parse_steps(origin_str)
        replace_steps = parse_steps(replace_str)

        for step_num, content in replace_steps.items():
            if "DELETE THIS STEP" in content:
                if step_num in origin_steps:
                    del origin_steps[step_num]
            else:
                origin_steps[step_num] = content

        sorted_steps = sorted(origin_steps.items())
        new_reasoning_steps = "\n\n".join([f"{content}" for num, content in sorted_steps])

        return new_reasoning_steps

    # ---------------------- Initialize Collection Structure ----------------------
    batch_output_records = []

    start_time = time.time()
    turn = 0

    # Main loop until all sequences are finished or maximum turns reached
    while True:
        sequences_needing_generation = [seq for seq in active_sequences if not seq['finished']]

        if sequences_needing_generation:
            turn += 1
            print(f'\n-------------- Turn {turn} --------------')
            print(f"We have {len(sequences_needing_generation)} sequences needing generation...")
            outputs = run_generation(sequences_needing_generation, max_tokens)
            print("Generation completed, processing outputs...")

            # Initialize batch variables
            batch_relevant_info = []
            batch_original_questions = []
            batch_prev_reasonings = []
            batch_search_queries = []
            batch_documents = []
            batch_sequences = []

            # Process each sequence
            for seq, out in zip(sequences_needing_generation, outputs):
                text = out.outputs[0].text
                seq['history'].append(text)
                seq['prompt'] += text
                seq['output'] += text

                # Extract search query
                search_query = extract_between(text, BEGIN_SEARCH_QUERY, END_SEARCH_QUERY)

                if search_query and seq['output'].rstrip().endswith(END_SEARCH_QUERY):
                    if seq['search_count'] < MAX_SEARCH_LIMIT and search_query not in seq['executed_search_queries']:
                        # Execute Wikipedia search
                        if search_query in search_cache:
                            results = search_cache[search_query]
                            print(f"Using cached search results for query: \"{search_query}\"")
                        else:
                            try:
                                results = wikipedia_search(search_query, top_k=top_k)
                                search_cache[search_query] = results
                                print(f"Executed and cached search for query: \"{search_query}\"")
                            except Exception as e:
                                print(f"Error during search query '{search_query}': {e}")
                                search_cache[search_query] = []
                                results = []

                        # Extract relevant information
                        relevant_info = extract_relevant_info(results)
                        seq['relevant_info'] = relevant_info

                        # Format documents
                        formatted_documents = ""
                        for i, doc_info in enumerate(relevant_info):
                            # Truncate article content if it exceeds max_doc_len
                            if 'content' in doc_info and len(doc_info['content']) > max_doc_len:
                                doc_info['content'] = doc_info['content'][:max_doc_len] + "..."
                            formatted_documents += f"**Wikipedia Article {i + 1}:**\n"
                            formatted_documents += json.dumps(doc_info, ensure_ascii=False, indent=2) + "\n"

                        # Collect parameters for batch processing
                        batch_relevant_info.append(relevant_info)
                        batch_original_questions.append(seq['item']['Question'])
                        batch_prev_reasonings.append(seq['output'])
                        batch_search_queries.append(search_query)
                        batch_documents.append(formatted_documents)
                        batch_sequences.append(seq)

                        # Update search count and executed queries
                        seq['search_count'] += 1
                        seq['executed_search_queries'].add(search_query)

                    elif seq['search_count'] >= MAX_SEARCH_LIMIT:
                        limit_message = f"\n{BEGIN_SEARCH_RESULT}\nThe maximum search limit is exceeded. You are not allowed to search.\n{END_SEARCH_RESULT}\n"
                        seq['prompt'] += limit_message
                        seq['output'] += limit_message
                        seq['history'].append(limit_message)
                        print(f"Search limit reached for query: \"{search_query}\"")

                    elif search_query in seq['executed_search_queries']:
                        limit_message = f"\n{BEGIN_SEARCH_RESULT}\nYou have searched this query. Please refer to previous results.\n{END_SEARCH_RESULT}\n"
                        seq['prompt'] += limit_message
                        seq['output'] += limit_message
                        seq['history'].append(limit_message)
                        print(f"Repeated search for query: \"{search_query}\"")

                else:
                    seq['finished'] = True
                    print("Sequence marked as complete.")

            # Process batch results
            if batch_sequences:
                print(f"Processing {len(batch_sequences)} sequences with search results...")
                webpage_analyses = generate_webpage_to_reasonchain_batch(
                    original_questions=batch_original_questions,
                    prev_reasonings=batch_prev_reasonings,
                    search_queries=batch_search_queries,
                    documents=batch_documents,
                    dataset_name=dataset_name,
                    batch_output_records=batch_output_records,
                    max_tokens=max_tokens,
                )

                for seq, analysis in zip(batch_sequences, webpage_analyses):
                    if isinstance(analysis, str):
                        append_text = f"\n\n{BEGIN_SEARCH_RESULT}{analysis}{END_SEARCH_RESULT}\n\n"
                        seq['prompt'] += append_text
                        seq['output'] += append_text
                        seq['history'].append(append_text)
                    else:
                        append_text = replace_recent_steps(seq['output'], analysis)
                        seq['prompt'] += append_text
                        seq['output'] += append_text
                        seq['history'].append(append_text)

        # Check if all sequences are finished
        unfinished = [seq for seq in active_sequences if not seq['finished']]
        if not unfinished:
            break
        else:
            if turn >= MAX_TURN:
                print(f"Maximum number of turns ({MAX_TURN}) reached, stopping.")
                break

    total_time = time.time() - start_time

    # Save batch output records
    t = time.localtime()
    batch_output_file = os.path.join(output_dir, f'{split}.{t.tm_mon}.{t.tm_mday},{t.tm_hour}:{t.tm_min}.info_extract.json')
    with open(batch_output_file, 'w', encoding='utf-8') as f:
        json.dump(batch_output_records, f, ensure_ascii=False, indent=2)

    print(f"Batch outputs saved to {batch_output_file}")

    # Prepare output list for evaluation
    output_list = [{'outputs': [{'text': seq['output']}]} for seq in active_sequences]

    # Run evaluation
    run_evaluation(
        filtered_data=filtered_data,
        input_list=[seq['prompt'] for seq in active_sequences],
        output_list=output_list,
        dataset_name=dataset_name,
        output_dir=output_dir,
        total_time=total_time,
        split=split
    )

    # Save search cache
    save_caches()
    print("Process completed.")

if __name__ == "__main__":
    main() 



Action 1: Search[VIVA Media AG rename in 2004 reason]
<|begin_search_result|>Could not find [VIVA Media AG rename in 2004 reason]. Similar: ['Vauxhall Viva', '2025 in Philippine television', 'Bosch (company)', 'Chocolate-coated marshmallow treats', '2023 in Philippine television', 'Chiquita', '2024 in Philippine television', 'El Dorado International Airport', 'Economy of Israel', 'Volkswagen Beetle']<|end_search_result|>
Observation 1: <|begin_search_result|>Error: name 'end' is not defined<|end_search_result|>
