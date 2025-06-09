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



Action 1: Search[VIVA Media AG rename in 2004 reason]
<|begin_search_result|>Could not find [VIVA Media AG rename in 2004 reason]. Similar: ['Vauxhall Viva', '2025 in Philippine television', 'Bosch (company)', 'Chocolate-coated marshmallow treats', '2023 in Philippine television', 'Chiquita', '2024 in Philippine television', 'El Dorado International Airport', 'Economy of Israel', 'Volkswagen Beetle']<|end_search_result|>
Observation 1: <|begin_search_result|>Error: name 'end' is not defined<|end_search_result|>
