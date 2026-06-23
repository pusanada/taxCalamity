# Prompt Engineering Techniques

Advanced prompt engineering patterns for production LLM applications.

## Core Techniques

### 1. Chain-of-Thought (CoT)

**Zero-shot CoT:**
```
Question: If there are 3 cars and each has 4 wheels, how many wheels total?

Let's think step by step.
```

**Few-shot CoT:**
```
Q: A store has 5 apples. 2 are sold. How many remain?
A: Let me work through this:
   - Start with 5 apples
   - Subtract 2 sold: 5 - 2 = 3
   - Answer: 3 apples

Q: [Your actual question]
A: Let me work through this:
```

### 2. Few-Shot Learning

**Example Selection Strategies:**
- **Semantic similarity**: Select examples closest to the query
- **Diversity sampling**: Cover different categories/types
- **Difficulty gradient**: Start easy, increase complexity

```python
# Dynamic example selection
similar_examples = vectorstore.similarity_search(query, k=3)
prompt = build_prompt(examples=similar_examples, query=query)
```

### 3. Constitutional AI

Self-critique and revision pattern:
```
Generate a response, then:

1. Critique: Does this response violate any principles?
   - Is it harmful?
   - Is it factually incorrect?
   - Is it biased?

2. Revise: If any issues found, revise the response.

3. Final Answer: Output the revised response.
```

### 4. Tree-of-Thoughts

Explore multiple reasoning paths:
```
Problem: [Complex problem]

Path A: [First approach]
  - Step 1: ...
  - Evaluation: Promising / Dead end

Path B: [Second approach]
  - Step 1: ...
  - Evaluation: Promising / Dead end

Best Path: [Select most promising and continue]
```

## Prompt Structure

### Standard Template
```
[System Context]
You are a [role] with expertise in [domain].

[Task Instruction]
Your task is to [specific action].

[Constraints]
- Constraint 1
- Constraint 2

[Examples] (if few-shot)
Input: ...
Output: ...

[Input Data]
{user_input}

[Output Format]
Provide your response in [format].
```

### System Prompt Design

```python
system_prompt = """You are an expert data analyst. Follow these guidelines:

CAPABILITIES:
- Analyze datasets and identify patterns
- Generate SQL queries for data retrieval
- Create visualizations recommendations

CONSTRAINTS:
- Always verify data assumptions
- Never make up statistics
- Cite sources when available

OUTPUT FORMAT:
- Use markdown for formatting
- Include confidence levels for insights
- Separate facts from interpretations"""
```

## Production Patterns

### 1. Structured Outputs

Force JSON output:
```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_object"}
)
```

With schema validation:
```python
from pydantic import BaseModel

class Analysis(BaseModel):
    summary: str
    key_findings: list[str]
    confidence: float

response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[{"role": "user", "content": prompt}],
    response_format=Analysis
)
```

### 2. Error Recovery

```
Attempt to [task]. If you cannot complete it:
1. Explain what information is missing
2. Provide a partial answer if possible
3. Suggest alternative approaches

Never say "I don't know" without explanation.
```

### 3. Self-Verification

```
After generating your response:

VERIFY:
[ ] Does it directly answer the question?
[ ] Is it based on the provided context?
[ ] Are all claims supported?
[ ] Is it free from harmful content?

If any check fails, revise before outputting.
```

## Optimization Strategies

### Token Efficiency
- Remove redundant instructions
- Use abbreviations after first definition
- Move stable content to system prompts
- Compress examples with representative cases

### Reliability
- Use temperature=0 for deterministic outputs
- Add explicit format constraints
- Include edge case handling
- Test with adversarial inputs

### Cost Control
- Start with smaller models
- Cache common prompts
- Batch similar requests
- Monitor token usage

## Common Pitfalls

1. **Vague Instructions**: Be specific about desired output
2. **Example Pollution**: Ensure examples match task exactly
3. **Context Overflow**: Manage token limits carefully
4. **Instruction Drift**: Reinforce key instructions at end
5. **Ignoring Edge Cases**: Test with unusual inputs

## A/B Testing Prompts

```python
class PromptABTest:
    def __init__(self):
        self.variants = {}
        self.results = defaultdict(list)
    
    def add_variant(self, name: str, prompt: str):
        self.variants[name] = prompt
    
    def run_test(self, inputs: list, evaluation_fn):
        for input in inputs:
            variant = random.choice(list(self.variants.keys()))
            response = llm.complete(self.variants[variant], input)
            score = evaluation_fn(input, response)
            self.results[variant].append(score)
    
    def analyze(self):
        for variant, scores in self.results.items():
            print(f"{variant}: mean={np.mean(scores):.3f}, std={np.std(scores):.3f}")
```
