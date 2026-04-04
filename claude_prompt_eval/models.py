from dataclasses import dataclass

USER_ROLE = "user"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_MAX_TOKENS = 1024


@dataclass
class PromptVersion:
    """A named version of a system prompt to evaluate."""
    name: str
    system_prompt: str
    model: str = DEFAULT_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS


@dataclass
class EvalCase:
    """A single input to test against each prompt version."""
    name: str
    user_message: str


@dataclass
class EvalResult:
    """The result of running one test case against one prompt version."""
    version_name: str
    test_name: str
    user_message: str
    response: str
    input_tokens: int
    output_tokens: int


@dataclass
class ScoreResult:
    """The scored evaluation of a single EvalResult."""
    version_name: str
    test_name: str
    score: int
    strengths: str
    weaknesses: str


@dataclass
class GradeReport:
    """Averaged grade across all test cases for a prompt version."""
    version_name: str
    avg_score: float
    num_cases: int
    scores: list[ScoreResult]
    recommendations: list[str]
