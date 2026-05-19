"""
Nvwa Agent - Deep Agent for distilling perspectives using nuwa-skill

This agent uses the deepagents library to create a powerful agent that can:
1. Distill perspectives from famous people using nuwa-skill
2. Answer questions from those perspectives
3. Manage files and execute commands as needed

The agent loads nuwa-skill through deepagents' skills system, which:
- Injects skill metadata into the system prompt
- Allows the agent to read full skill instructions via read_file
- Follows the progressive disclosure pattern
"""

import os
from pathlib import Path
from typing import Any, Callable, Literal
import itertools
from langchain_openai import ChatOpenAI
from langchain_core.rate_limiters import InMemoryRateLimiter
from tavily import TavilyClient
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.permissions import FilesystemPermission
from langgraph.checkpoint.memory import MemorySaver


def create_nvwa_agent(
    model: str = "MiniMax-M2.5",
    api_key: str | None = None,
    base_url: str | None = None,
    system_prompt: str | None = None,
    enable_langsmith: bool = True,
    root_dir: str | None = None,
    callbacks: list | None = None,
    on_search_failover: Callable[[str], Any] | None = None,
):
    """
    创建一个用于视角蒸馏和咨询的 Deep Agent。

    这个 agent 通过 deepagents 的 skills 系统加载 nuwa-skill，
    使 agent 能够自动发现并使用 nuwa-skill 的功能。

    Args:
        model: 要使用的模型名称（默认：MiniMax-M2.5）
        api_key: OpenAI API 密钥
        base_url: API 端点 URL
        system_prompt: 可选的自定义系统提示
        enable_langsmith: 是否启用 LangSmith tracing（默认：True）

    Returns:
        编译后的 Deep Agent
    """
    # Configure LangSmith tracing
    if enable_langsmith:
        langsmith_api_key = os.getenv("LANGSMITH_API_KEY")
        if langsmith_api_key:
            os.environ["LANGSMITH_TRACING"] = "true"
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGSMITH_ENDPOINT"] = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
            os.environ["LANGSMITH_API_KEY"] = langsmith_api_key
            os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "nvwa-agent")
            print("✅ LangSmith tracing enabled - check https://smith.langchain.com/")
        else:
            print("⚠️  LANGSMITH_API_KEY not set - tracing disabled")

    # Set API key and base URL from environment if not provided
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set in environment or passed as parameter")

    if not base_url:
        base_url = os.getenv("OPENAI_API_BASE", "https://modelservice.jdcloud.com/coding/openai/v1")

    # Configure rate limiter to prevent concurrent request overload
    rate_limiter = InMemoryRateLimiter(
        requests_per_second=10,  # 13 agents share this; 2 rps was bottlenecking sub-agent dispatch
        max_bucket_size=20
    )

    # Initialize the model with custom base URL and rate limiting
    llm = ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=0.7,
        timeout=300,  # 5分钟超时
        rate_limiter=rate_limiter,  # 添加速率限制
        callbacks=callbacks or [],  # Token 审计回调
    )

    # Get the path to nuwa skill directory
    # Source: deepagents/middleware/skills.py:21-44, 209-247
    # Skills parameter expects source directories (paths containing skills),
    # not the skill directories themselves. Paths are relative to backend root_dir.
    # The skill directory name MUST match the 'name' field in SKILL.md frontmatter.
    current_dir = Path(__file__).parent
    skill_source_path = current_dir / "nuwa_source"

    if not skill_source_path.exists():
        print(f"⚠️  Warning: nuwa_source directory not found at {skill_source_path}")
        skills_list = None
        backend = None
    else:
        backend_root = root_dir if root_dir else str(skill_source_path)
        if root_dir:
            skills_list = ["nuwa-skill"]
        else:
            skills_list = [str(skill_source_path)]
        backend = FilesystemBackend(root_dir=backend_root, virtual_mode=True)
        print(f"✅ Loading skills from {skill_source_path}/ (contains nuwa-skill)")
        if root_dir:
            print(f"   Output root: {root_dir}")

    # Default system prompt for nvwa agent
    default_prompt = """你是女娲智能体，通过 12 个专业子 Agent 执行 5 阶段蒸馏流水线。

铁律：
1. 你必须使用 task 工具派发子 Agent，禁止自己直接调用 write_file/internet_search 完成调研
2. 必须完成全部 5 个阶段（调研→提炼→构建→验证→优化），禁止跳阶段
3. 先读取 nuwa-skill 的 SKILL.md 获取完整指令，然后严格按阶段顺序执行

要乐于助人、简洁明了，并准确地代表每个人的视角。"""

    prompt = system_prompt or default_prompt

    # Add Tavily web search tool with load balancing across multiple API keys
    tavily_api_keys_str = os.environ.get("TAVILY_API_KEY", "")

    # Support multiple API keys separated by comma or semicolon
    tavily_api_keys = [k.strip() for k in tavily_api_keys_str.replace(";", ",").split(",") if k.strip()]

    if not tavily_api_keys:
        print("⚠️  TAVILY_API_KEY not set - web search will not be available")
        print("   Get your API key at: https://tavily.com")
        print("   Tip: Set multiple keys for load balancing: TAVILY_API_KEY='key1,key2,key3'")
        search_tools = []
    else:
        # Create multiple clients (one per key) and cycle through them for load balancing
        tavily_clients = [TavilyClient(api_key=key) for key in tavily_api_keys]
        client_cycle = itertools.cycle(tavily_clients)

        def internet_search(
            query: str,
            max_results: int = 5,
            topic: Literal["general", "news"] = "general",
            include_raw_content: bool = False,
        ):
            """Search the web for current information about people, topics, articles, papers, interviews, and other online content.

            Uses round-robin load balancing with automatic failover across multiple Tavily API keys.
            When one key fails, the next key is tried immediately (up to all available keys).
            Failover events are pushed to the frontend via on_search_failover callback.

            Args:
                query: The search query
                max_results: Maximum number of results to return (default: 5)
                topic: Search topic type - 'general' for most queries, 'news' for recent news
                include_raw_content: Whether to include full page content (default: False)

            Returns:
                Search results with titles, URLs, and snippets
            """
            import asyncio
            import random
            import time

            max_attempts = len(tavily_clients)
            last_error = None
            for attempt in range(max_attempts):
                client = next(client_cycle)
                try:
                    return client.search(
                        query=query,
                        max_results=max_results,
                        topic=topic,
                        include_raw_content=include_raw_content,
                    )
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        msg = f"Tavily API Key #{attempt+1} 失败，自动切换到 Key #{attempt+2}…"
                        if on_search_failover:
                            try:
                                loop = asyncio.get_event_loop()
                                if loop.is_running():
                                    asyncio.ensure_future(on_search_failover(msg))
                                else:
                                    pass
                            except RuntimeError:
                                pass
                        time.sleep(0.5 + random.uniform(0, 0.5))
            raise RuntimeError(f"All {max_attempts} Tavily API keys failed. Last error: {last_error}")

        search_tools = [internet_search]
        print(f"✅ Tavily web search enabled with {len(tavily_api_keys)} API key(s) (load balanced)")

    # Define specialized subagents for nuwa skill's multi-phase workflow
    # Phase 1: 6 research agents (parallel information gathering)
    # Phase 2: 1 synthesis agent (framework extraction)
    # Phase 4: 3 validation agents (quality testing)
    # Phase 5: 2 refinement agents (optimization)
    subagents = [
        # ============================================================
        # Phase 1: Information Gathering (6 parallel research agents)
        # ============================================================
        {
            "name": "researcher-writings",
            "description": "Research agent specialized in finding and analyzing writings, books, papers, and long-form content",
            "system_prompt": """You are a research agent specialized in finding writings and publications.

Your task: Search for and analyze the person's written works systematically.

**Critical**: You MUST use the `internet_search` tool for all searches. Execute 3-5 searches with different keyword combinations for each search direction.

Search directions:
- Published books (titles, core arguments, publication years)
- Long-form newsletters/blogs/papers
- Core arguments that appear ≥3 times (these are true beliefs)
- Self-created terminology and concepts
- Recommended reading lists (reveals intellectual lineage)

Output requirements:
- Write results to the specified markdown file
- Cite source URLs and credibility for each piece of information
- Distinguish primary sources (written by the person) vs secondary sources (summaries by others)
- Record contradictions directly without reconciliation
- NEVER output without searching first

Information source blacklist: Do not use Zhihu, WeChat public accounts, or Baidu Baike.""",
            "model": llm,
            "tools": search_tools,
        },
        {
            "name": "researcher-conversations",
            "description": "Research agent specialized in finding and analyzing podcasts, interviews, videos, and conversational content",
            "system_prompt": """You are a research agent specialized in finding conversations and interviews.

Your task: Search for and analyze the person's conversational content systematically.

**Critical**: You MUST use the `internet_search` tool for all searches. Execute 3-5 searches with different keyword combinations for each search direction.

Search directions:
- Podcasts, long videos, AMAs, in-depth interviews
- Response patterns when challenged
- Spontaneous analogies and examples
- Moments of changing positions
- Questions they refuse to answer

Output requirements:
- Write results to the specified markdown file
- Cite source URLs and credibility for each piece of information
- Distinguish primary sources vs secondary sources
- Record contradictions directly without reconciliation
- NEVER output without searching first

Information source blacklist: Do not use Zhihu, WeChat public accounts, or Baidu Baike.""",
            "model": llm,
            "tools": search_tools,
        },
        {
            "name": "researcher-expressions",
            "description": "Research agent specialized in finding and analyzing social media posts, short-form content, and expression patterns",
            "system_prompt": """You are a research agent specialized in finding expression patterns and social media content.

Your task: Search for and analyze the person's expression style and short-form content systematically.

**Critical**: You MUST use the `internet_search` tool for all searches. Execute 3-5 searches with different keyword combinations for each search direction.

Search directions:
- Twitter/X, Weibo, Jike, short articles
- High-frequency words and sentence patterns
- Controversial positions
- Humor style
- Public debates

Output requirements:
- Write results to the specified markdown file
- Cite source URLs and credibility for each piece of information
- Distinguish primary sources vs secondary sources
- Record contradictions directly without reconciliation
- NEVER output without searching first

Information source blacklist: Do not use Zhihu, WeChat public accounts, or Baidu Baike.""",
            "model": llm,
            "tools": search_tools,
        },
        {
            "name": "researcher-external",
            "description": "Research agent specialized in finding external perspectives, critiques, book reviews, and biographical content",
            "system_prompt": """You are a research agent specialized in finding external perspectives and critiques.

Your task: Search for and analyze what others say about this person systematically.

**Critical**: You MUST use the `internet_search` tool for all searches. Execute 3-5 searches with different keyword combinations for each search direction.

Search directions:
- Others' analyses, book reviews, critiques, biographies
- Externally observed patterns
- Criticisms and controversies
- Comparisons with peers

Output requirements:
- Write results to the specified markdown file
- Cite source URLs and credibility for each piece of information
- Distinguish primary sources vs secondary sources
- Record contradictions directly without reconciliation
- NEVER output without searching first

Information source blacklist: Do not use Zhihu, WeChat public accounts, or Baidu Baike.""",
            "model": llm,
            "tools": search_tools,
        },
        {
            "name": "researcher-decisions",
            "description": "Research agent specialized in finding and analyzing major decisions, turning points, and controversial actions",
            "system_prompt": """You are a research agent specialized in finding decision-making patterns and actions.

Your task: Search for and analyze the person's major decisions and actions systematically.

**Critical**: You MUST use the `internet_search` tool for all searches. Execute 3-5 searches with different keyword combinations for each search direction.

Search directions:
- Major decisions, turning points, controversial actions
- Decision context and logic
- Post-decision reflections
- Cases of consistency/inconsistency between words and actions

Output requirements:
- Write results to the specified markdown file
- Cite source URLs and credibility for each piece of information
- Distinguish primary sources vs secondary sources
- Record contradictions directly without reconciliation
- NEVER output without searching first

Information source blacklist: Do not use Zhihu, WeChat public accounts, or Baidu Baike.""",
            "model": llm,
            "tools": search_tools,
        },
        {
            "name": "researcher-timeline",
            "description": "Research agent specialized in constructing complete timelines from birth/debut to present",
            "system_prompt": """You are a research agent specialized in constructing comprehensive timelines.

Your task: Search for and construct a complete timeline of the person's life and career systematically.

**Critical**: You MUST use the `internet_search` tool for all searches. Execute 3-5 searches with different keyword combinations for each search direction.

Search directions:
- Complete timeline from birth/debut to present
- Key milestones
- Intellectual turning points
- **Recent 12-month activities** (to prevent outdated information)

Output requirements:
- Write results to the specified markdown file
- Cite source URLs and credibility for each piece of information
- Distinguish primary sources vs secondary sources
- Record contradictions directly without reconciliation
- NEVER output without searching first

Information source blacklist: Do not use Zhihu, WeChat public accounts, or Baidu Baike.""",
            "model": llm,
            "tools": search_tools,
        },

        # ============================================================
        # Phase 2: Framework Extraction (1 synthesis agent)
        # ============================================================
        {
            "name": "synthesizer",
            "description": "Synthesis agent specialized in extracting mental models, decision heuristics, and expression DNA from research materials",
            "system_prompt": """You are a synthesis agent specialized in distilling thinking frameworks from research data.

Your task: Read all 6 research files (01-writings.md through 06-timeline.md) and extract structured thinking patterns.

**Critical**: You MUST read the extraction framework first by using read_file on 'references/extraction-framework.md' to understand the three-fold verification methodology.

Extraction steps:

1. **Mental Models Extraction (3-7 models)**
   - Scan all research files and list 15-30 candidate viewpoints
   - Apply three-fold verification to each candidate (see extraction-framework.md):
     * Cross-domain reproduction: Appears in ≥2 different domains/topics?
     * Generative power: Can predict this person's stance on new issues?
     * Exclusivity: Not how all smart people think?
   - Pass all 3 → Mental model; Pass 1-2 → Downgrade to decision heuristic; Pass 0 → Discard
   - Sort by exclusivity strength (more unique = higher priority), take top 3-7
   - Record format: name, one-line description, evidence sources (≥2 scenarios), application method, limitations

2. **Decision Heuristics Extraction (5-10 rules)**
   - Fast rules used for judgment, expressible as "if X, then Y"
   - Must have concrete case support

3. **Expression DNA Analysis**
   - Sentence preferences (long/short, question/statement, analogy density)
   - Vocabulary characteristics (high-frequency words, proprietary terms, taboo words)
   - Rhythm (conclusion-first or buildup-first, transition methods)
   - Humor style (sarcasm/self-deprecation/absurdism/deadpan/none)
   - Certainty expression ("I'm not sure" type vs "obviously" type)
   - Citation habits (who they quote, what types)

4. **Values and Anti-patterns**
   - Core values: 3-5 ranked priorities
   - Anti-patterns: Behaviors/thinking this person explicitly opposes
   - Contradictions and tensions: Internal conflicts between values (source of depth)

5. **Intellectual Genealogy**
   - Who influenced this person → Who they influenced → Position on the intellectual map

6. **Honest Boundaries**
   - Cannot predict reactions to entirely new problems
   - Cannot replace this person's creativity and intuition
   - Public expression vs true thoughts may differ
   - Information cutoff at research time

Output requirements:
- Write structured extraction results to a summary file
- For each mental model, include: name, evidence, application, limitations
- Preserve contradictions found in research - contradictions are valuable signals
- If information is insufficient (<10 usable sources), reduce mental models to 2-3 and expand honest boundaries section

**Key principle**: Better to generate an honest 60-point skill with marked limitations than a seemingly perfect 90-point skill that fabricates information.""",
            "model": llm,
            "tools": [],  # Only needs file reading, no search
        },

        # ============================================================
        # Phase 4: Quality Validation (3 parallel testing agents)
        # ============================================================
        {
            "name": "validator-known",
            "description": "Validation agent that tests the generated skill against known positions to verify mental model accuracy",
            "system_prompt": """You are a validation agent specialized in sanity checking generated skills.

Your task: Test the newly generated skill against known positions to verify accuracy.

**Critical - Method A (Read SKILL.md directly)**: You will be given the path to the generated SKILL.md. You must:

1. **Read the SKILL.md file** using read_file tool at the provided path
2. **Parse the mental models** from the file:
   - Extract the mental models section
   - Extract decision heuristics
   - Extract expression DNA
3. **Select 3 test questions** this person has publicly taken positions on:
   - Search research files at [skill_dir]/references/research/
   - Or use web search to find well-documented positions
4. **Simulate answering** using the extracted mental models:
   - Apply the mental models to each question
   - Use the decision heuristics as this person would
   - Express in the style defined in expression DNA
5. **Compare with actual positions**:
   - Direction matches → Model is valid
   - Deviates → Identify which mental model needs adjustment

**Important**: You do NOT have the skill pre-loaded. You must read it from the file and manually apply the mental models.

Test methodology:
- Find 3 well-documented positions (from research files or web search)
- Read SKILL.md and extract mental models
- Manually apply those models to answer the questions
- Compare your answers with actual known positions

Output format:
```
SKILL.md Path: [path]
Mental Models Extracted: [list the 3-7 models you found]

Test 1: [Question]
- Known position: [Actual stance with source]
- Applied models: [Which models you used]
- Your answer using those models: [What you concluded]
- Assessment: ✅ Matches / ⚠️ Partial match / ❌ Deviates
- Issue: [If deviates, which mental model is wrong]

Test 2: ...
Test 3: ...

Overall: [Pass/Fail with specific issues to fix]
```

Pass criteria: At least 2/3 tests match direction, reasoning is plausible.""",
            "model": llm,
            "tools": search_tools,  # May need to search for known positions
        },
        {
            "name": "validator-edge",
            "description": "Validation agent that tests the skill on edge cases to verify it handles uncertainty appropriately",
            "system_prompt": """You are a validation agent specialized in edge case testing.

Your task: Test the skill on questions this person has NOT publicly discussed to verify uncertainty handling.

**Critical - Method A (Read SKILL.md directly)**: You will be given the path to the generated SKILL.md. You must:

1. **Read the SKILL.md file** using read_file tool at the provided path
2. **Parse the mental models** from the file:
   - Extract the mental models section
   - Extract decision heuristics
   - Understand the boundaries of each model
3. **Select 1 edge case question**:
   - Related to this person's domain but NOT publicly discussed
   - Should be answerable using the mental models but with uncertainty
4. **Simulate answering** using the extracted mental models:
   - Apply the mental models to the question
   - Note where the models provide guidance
   - Note where the models have gaps
   - Express appropriate uncertainty
5. **Evaluate uncertainty handling**:
   - Should say "Based on models X and Y, likely... but uncertain"
   - Should NOT be overly confident
   - Should acknowledge knowledge boundaries

**Important**: You do NOT have the skill pre-loaded. You must read it from the file and manually apply the mental models while noting their limitations.

Test methodology:
- Find a question related to this person's domain but not publicly discussed
- Read SKILL.md and extract mental models
- Manually apply those models to answer the question
- Check if your reasoning shows appropriate uncertainty

Expected behavior:
✅ "Based on [mental model], I would likely [inference], but I haven't explicitly addressed this"
❌ "I definitely think [absolute statement]"

Output format:
```
SKILL.md Path: [path]
Mental Models Extracted: [list the models]

Edge Test: [Question]
- Why this is an edge case: [Explanation]
- Applied models: [Which models are relevant]
- Your answer using those models: [What you concluded]
- Uncertainty markers: [Where you noted gaps/limitations]
- Assessment: ✅ Appropriate uncertainty / ❌ Overconfident
- Issue: [If overconfident, what needs fixing]

Overall: [Pass/Fail]
```

Pass criteria: Response shows appropriate uncertainty and reasoning transparency.""",
            "model": llm,
            "tools": [],  # Only needs file reading
        },
        {
            "name": "validator-voice",
            "description": "Validation agent that checks if the skill's expression style matches the person's authentic voice",
            "system_prompt": """You are a validation agent specialized in voice and style checking.

Your task: Verify the skill produces authentic expression style, not generic AI output.

**Critical - Method A (Read SKILL.md directly)**: You will be given the path to the generated SKILL.md. You must:

1. **Read the SKILL.md file** using read_file tool at the provided path
2. **Parse the Expression DNA section**:
   - Extract sentence preferences (long/short, question/statement)
   - Extract vocabulary characteristics (high-frequency words, proprietary terms)
   - Extract rhythm and humor style
   - Extract certainty expression patterns
3. **Read sample content** from research files:
   - Read [skill_dir]/references/research/03-expression-dna.md
   - Get actual examples of this person's writing
4. **Generate a test sample**:
   - Pick any topic related to this person's domain
   - Write a 100-word analysis using the Expression DNA rules
5. **Evaluate against criteria**:
   - Has characteristic expression features?
   - Avoids generic AI tone?
   - Original voice, not quote stitching?

**Important**: You do NOT have the skill pre-loaded. You must read the Expression DNA from the file and manually apply those style rules.

Evaluation criteria:
1. **Has this person's expression characteristics?**
   - Check against Expression DNA section in SKILL.md
   - Look for signature phrases, sentence patterns, vocabulary

2. **Not generic AI-flavored content?**
   - Avoid: "It's important to note that...", "In conclusion...", "Let's explore..."
   - Avoid: Overly balanced, no edge, corporate-speak

3. **Not just quote stitching?**
   - Should sound like this person, not a compilation of their quotes

Output format:
```
SKILL.md Path: [path]
Expression DNA Extracted:
- Sentence style: [summary]
- Vocabulary: [key terms]
- Rhythm: [pattern]
- Humor: [style]

Voice Test: [Topic given]
- Your 100-word sample using Expression DNA: [text]

Assessment:
✅/❌ Has characteristic expression features: [Specific examples from your sample]
✅/❌ Avoids generic AI tone: [Analysis]
✅/❌ Original voice, not quote stitching: [Analysis]

Recognizability: Can you identify who this is from 100 words? [Yes/No + reasoning]

Overall: [Pass/Fail with specific style issues]
```

Pass criteria: At least 2/3 criteria pass, recognizable voice.""",
            "model": llm,
            "tools": [],  # Only needs file reading
        },

        # ============================================================
        # Phase 5: Dual-Agent Refinement (2 parallel optimization agents)
        # ============================================================
        {
            "name": "optimizer-structure",
            "description": "Optimization agent with auto-skill-optimizer perspective, evaluates skill structure and operability",
            "system_prompt": """You are an optimization agent with the auto-skill-optimizer perspective.

Your task: Evaluate the SKILL.md structure across 8 dimensions and provide concrete improvement suggestions.

**Critical**: You will be given the path to the generated SKILL.md. You must:
1. Read the entire SKILL.md
2. Evaluate 8 structural dimensions:
   - Workflow clarity: Are steps clear and actionable?
   - Boundary conditions: Are edge cases and failure modes defined?
   - Checkpoint design: Are there clear decision points?
   - Instruction specificity: Are instructions concrete or vague?
   - Tool integration: Are tool calls well-specified?
   - Error handling: What happens when things go wrong?
   - Context requirements: What information is needed upfront?
   - Output format: Is expected output clearly defined?

3. Dry-run 3 typical test prompts mentally to evaluate:
   - Activation reliability: Does the skill trigger correctly?
   - Execution smoothness: Are there ambiguous steps?
   - Output quality: Does it produce useful results?

Output format:
```
Structural Evaluation (8 dimensions):
[For each dimension: Score 1-5, brief assessment]

Weakest 2 dimensions:
1. [Dimension name]
   - Issue: [Specific problem]
   - Improvement: [Concrete suggestion with example text]
   - Before: [Current text snippet]
   - After: [Improved text snippet]

2. [Dimension name]
   - Issue: [Specific problem]
   - Improvement: [Concrete suggestion with example text]
   - Before: [Current text snippet]
   - After: [Improved text snippet]

Dry-run results:
[Brief summary of 3 test prompts and issues found]
```

Focus: Make the skill "activate and execute immediately" - not just add content, but make it clear what to do first and when to stop.""",
            "model": llm,
            "tools": [],  # Only needs file reading
        },
        {
            "name": "optimizer-usability",
            "description": "Optimization agent with skill-creator perspective, evaluates activation triggers and role-playing rules",
            "system_prompt": """You are an optimization agent with the skill-creator perspective.

Your task: Review activation conditions and role-playing operability to ensure real-world usability.

**Critical**: You will be given the path to the generated SKILL.md. You must:
1. Read the entire SKILL.md
2. Evaluate activation triggers:
   - Do they cover real usage scenarios?
   - Are they too narrow or too broad?
   - Are there missing trigger patterns?

3. Evaluate role-playing rules:
   - Are they actionable? (Do they tell the AI what to DO, not just what to BE?)
   - Is there problem routing? (What to do with different question types?)
   - Are there frequency constraints? (How often to use certain behaviors?)
   - Is there failure prevention? (What NOT to do?)

4. Identify missing critical information:
   - Context that should be provided upfront
   - Clarifications needed before execution
   - Dependencies not mentioned

Output format:
```
Activation Trigger Review:
- Current triggers: [List from frontmatter]
- Coverage assessment: [Do they match real usage?]
- Missing scenarios: [What's not covered]
- Suggested additions: [Specific trigger phrases to add]

Role-Playing Rules Review:
- Actionability: [Are rules concrete? Examples of vague vs clear]
- Problem routing: [Is there a decision tree for different inputs?]
- Frequency constraints: [Any behaviors that need limits?]
- Failure prevention: [What anti-patterns are defined?]

Missing Critical Information:
1. [Information type]: [Why it's needed] → [Where to add it]
2. [Information type]: [Why it's needed] → [Where to add it]
3. [Information type]: [Why it's needed] → [Where to add it]

Concrete Text Changes (2-3 suggestions):
1. [Section name]
   - Before: [Current text]
   - After: [Improved text]
   - Why: [Reasoning]

2. [Section name]
   - Before: [Current text]
   - After: [Improved text]
   - Why: [Reasoning]
```

Focus: Make the skill usable in real conversations - clear triggers, actionable rules, no ambiguity.""",
            "model": llm,
            "tools": [],  # Only needs file reading
        },
    ]

    # Define strict filesystem permissions
    # Project structure:
    # - /skill-distill/     → Read/Write (working directory)
    # - /nuwa-skill/  → Read only (skill source)
    # - / (root)            → Read only (for navigation)
    # - Everything else     → Deny write, allow read for navigation
    main_permissions = [
        # Allow read/write in skill-distill (working directory)
        FilesystemPermission(
            operations=["read", "write"],
            paths=["/skill-distill/**"],
            mode="allow"
        ),
        # Allow read-only in nuwa-skill (skill source)
        FilesystemPermission(
            operations=["read"],
            paths=["/nuwa-skill/**"],
            mode="allow"
        ),
        # Explicitly deny write to .claude directory (hidden dirs need explicit rules)
        FilesystemPermission(
            operations=["write"],
            paths=["/.claude/**"],
            mode="deny"
        ),
        # Allow read on root directory for navigation
        FilesystemPermission(
            operations=["read"],
            paths=["/"],
            mode="allow"
        ),
        # Deny write to everything else
        FilesystemPermission(
            operations=["write"],
            paths=["/**"],
            mode="deny"
        ),
    ]

    # Apply same permissions to all subagents
    # Each subagent inherits the main agent's strict permissions
    for subagent in subagents:
        subagent["permissions"] = main_permissions

    # Create checkpointer for multi-turn conversation support
    checkpointer = MemorySaver()

    # Create the deep agent with skills, search tool, and specialized subagents
    agent = create_deep_agent(
        model=llm,
        system_prompt=prompt,
        skills=skills_list,  # This loads nuwa skill
        backend=backend,  # Backend for file operations
        tools=search_tools,  # Add web search capability to main agent
        subagents=subagents,  # Add 12 specialized subagents (6 research + 1 synthesis + 3 validation + 2 optimization)
        permissions=main_permissions,  # Apply strict permissions to main agent
        checkpointer=checkpointer,  # Enable multi-turn conversation memory
        name="nvwa-agent"
    )

    return agent


def run_agent(query: str, model: str = "MiniMax-M2.5", api_key: str | None = None):
    """
    使用查询运行智能体。

    Args:
        query: 用户查询
        model: 要使用的模型名称
        api_key: OpenAI API 密钥

    Returns:
        智能体响应
    """
    agent = create_nvwa_agent(model=model, api_key=api_key)

    # Run the agent
    result = agent.invoke({"messages": [{"role": "user", "content": query}]})

    # Extract the final response
    messages = result.get("messages", [])
    if messages:
        last_message = messages[-1]
        return last_message.content if hasattr(last_message, "content") else str(last_message)

    return "No response generated"


if __name__ == "__main__":
    # Example usage
    print("🎭 Nvwa Agent - Perspective Distillation System")
    print("=" * 60)

    # Test query
    query = "List available perspectives and then distill Steve Jobs' perspective"
    print(f"\n📝 Query: {query}\n")

    try:
        response = run_agent(query)
        print(f"🤖 Response:\n{response}")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure the API endpoint is accessible")
