# Code Change Philosophy

## Keep Changes Small and Focused

- One logical change per commit — each commit should do exactly one thing
- If a task feels too large, break it into subtasks
- Prefer multiple small commits over one large commit
- Run feedback loops after each change, not at the end
- Quality over speed. Small steps compound into big progress.

## Task Prioritization

When choosing the next task, prioritize in this order:

1. **Architectural decisions and core abstractions** — Get the foundation right
2. **Integration points between modules** — Ensure components connect properly
3. **Unknown unknowns and spike work** — De-risk early
4. **Standard features and implementation** — Build on solid foundations
5. **Polish, cleanup, and quick wins** — Save easy wins for later

# Code Quality Standards

## Write Concise Code

After writing any code file, ask yourself: "Would a senior engineer say this is overcomplicated?"

If yes, simplify.

## Avoid Over-Engineering

- Only make changes that are directly requested or clearly necessary
- Don't add features beyond what was asked
- Don't refactor code that doesn't need it
- A bug fix doesn't need surrounding code cleaned up
- A simple feature doesn't need extra configurability

## Clean Code Practices

- Don't fill files just for the sake of it
- Don't leave dead code — if it's unused, delete it completely
- Be organized, concise, and clean in your work
- No backwards-compatibility hacks for removed code
- No `# removed` comments or re-exports for deleted items

## Task Decomposition

- Use micro tasks — smaller the task, better the code
- Break complex work into discrete, testable units
- Each micro task should be completable in one focused session

# Project-Specific Rules

## Tech Stack

- **Runtime**: Python 3.10+
- **Package Management**: pip + venv
- **Testing**: pytest
- **AI SDK**: Anthropic Python SDK
- **Environment**: python-dotenv

## Code Standards

- Use 4 spaces for indentation (PEP 8)
- Use snake_case for files, functions, and variables
- Use PascalCase for classes
- Keep imports organized — stdlib, third-party, local
- Extract magic strings into constants
- Use dependency injection — pass dependencies into classes, don't import globals

## Boundaries — Never Modify

- `.env` files during execution
- `venv/` directory contents
- `*.lock` files

## Testing

- Write tests for new features
- Run tests before committing: `make test`
- Mock external API calls — never hit the real Claude API in tests
- Use constants for test values — avoid hardcoded strings in assertions

## Commit Guidelines

- One logical change per commit
- Write descriptive commit messages
- Commit message format: `type: brief description`
  - `feat:` new feature
  - `fix:` bug fix
  - `refactor:` code restructuring
  - `docs:` documentation
  - `test:` test additions/changes
  - `chore:` maintenance tasks
