# Agentic AI Student Assistant

A beginner-friendly Python project demonstrating **LLM-driven tool selection**, safe local Python execution, returning tool results to the LLM, conversational history, and error handling.

This is an **educational demonstration using fictional student records**, not a real university data service.

## Architecture

User → Groq-hosted LLM chooses zero or more tools → Python validates the tool request → Approved local function runs → Structured result returns to LLM → Final response.

The LLM selects tools based on the meaning of the request; Python code does not route conversations by searching for words like "attendance".

### Tools

- **calculator** — Addition, subtraction, multiplication, division, percentages through a restricted arithmetic-expression parser (never arbitrary `eval()`).
- **get_student_info** — Case-insensitive department lookup.
- **get_attendance** — Case-insensitive attendance lookup.

The sample student dictionary contains fictional Arun (CSE, 82%) and Priya (AI, 91%).

## Setup in VS Code on Windows

1. Install Python 3.10+ and open the repository folder in VS Code.
2. In its PowerShell terminal, execute:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

3. Create a personal Groq API key at https://console.groq.com/keys.
4. Open your **local** `.env` file and replace the sample placeholder. **Never share or commit the real key.**
5. Run the deterministic offline tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

6. Start the application:

```powershell
.\.venv\Scripts\python.exe main.py
```

Use `/trace on` to inspect actual model-selected tool calls, `/trace off` to hide them, `/reset` to clear session history, and `/exit` to quit.

## Required evaluation prompts

| Prompt | Expected tool | Expected result |
| --- | --- | --- |
| Calculate 250 * 15 / 100 | calculator | 37.5 |
| What department does Arun belong to? | get_student_info | CSE |
| What is Priya's attendance? | get_attendance | 91% |
| What is Python? | No local tool needed | General explanation |
| What is Rahul's attendance? | get_attendance | Graceful not-found answer |

Additional examples: Ask "What is Arun's attendance?" and then "What department is he in?" to check conversational context; or ask "What percentage of 800 is 120?" to check a different arithmetic formulation.

**Test evidence:** The included offline pytest suite uses mock model responses. Passing these tests proves local tool and controller behavior, *not* that the live LLM always selects the expected tools. Run the five prompts against Groq and examine the actual trace before claiming live-model tests passed.

## Optional Docker deployment

Run Docker Desktop, then in the project folder:

```powershell
docker build -t student-assistant .
docker run --rm -it --env-file .env student-assistant
```

The Docker ignore file excludes `.env` from the image; the container receives its API key at runtime. Treat terminals and logs displaying tool arguments as potentially sensitive if you later use real records.

## Project files

| File | Purpose |
| --- | --- |
| `agent.py` | Model tool schemas, tool calling loop, result feedback, session memory |
| `tools.py` | Safe arithmetic and student lookup functions |
| `data.py` | Fictional student records |
| `main.py` | Interactive CLI |
| `tests/` | Deterministic unit tests and mocked agent tests |
| `Dockerfile` | Container deployment |
| `requirements.txt` | Python dependencies |
| `.env.example` | Public configuration example, **not** a real secret |
| `.gitignore`, `.dockerignore` | Protect secrets and exclude generated files |

## Safety and limitations

- The calculator accepts restricted arithmetic: `+`, `-`, `*`, `/`, parentheses, and unary signs. Percentage questions are translated into arithmetic by the LLM.
- Python executes only allowlisted functions and checks argument types. The tool-call loop is limited to five rounds.
- Unknown names, malformed inputs, divide-by-zero, and API failures are handled.
- The model may still choose a wrong tool or produce an incorrect answer; observe and test the actual result.
- No authentication, real institutional database, role-based permissions, or permanent conversation storage are included.
- Do **not** add genuine private student records or credentials to a public repository.
- Groq API use may incur costs or rate limits.
- This project is provided for learning and class evaluation; consider a license deliberately before granting reuse rights.

## Official documentation

- https://console.groq.com/docs/tool-use/local-tool-calling
- https://console.groq.com/docs/models
- https://console.groq.com/docs/rate-limits

## Viva explanation

"The LLM reads the question and the descriptions of three available tools. It either answers directly or requests a suitable tool. My Python controller validates the request, executes only approved local Python functions, sends structured results back to the LLM, and returns the model's final answer. Conversation history supports follow-up questions."
