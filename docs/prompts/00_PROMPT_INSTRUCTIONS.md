# 🤖 AI Prompt Templates — How to Use

## What Are These?

Each `.md` file in this folder is a **ready-to-paste prompt** for an AI coding assistant (Claude, Gemini, ChatGPT, Cursor, etc.). Your team member pastes the prompt, attaches the referenced files, and the AI generates all the code for that module.

## How to Use

### Step 1: Make Sure Core Module is Built First
The `01_core_module.md` prompt **must be run first** by whoever is assigned the Core module. All other modules depend on the code it generates.

### Step 2: Each Team Member Gets Their Prompt
| Prompt File | Module | Can Start After |
|-------------|--------|----------------|
| `01_core_module.md` | Core + Config | Immediately |
| `02_input_module.md` | Input Processing | Core is done |
| `03_transliteration_module.md` | Transliteration | Core is done |
| `04_extraction_module.md` | Entity Extraction | Core is done |
| `05_research_module.md` | Entity Research | Core is done |
| `06_explanation_module.md` | Explanation Gen | Core is done |
| `07_response_module.md` | Response Compilation | Core is done |
| `08_server_module.md` | FastAPI Server | Core is done |
| `09_frontend_module.md` | React Frontend | Core is done |

### Step 3: Paste Into AI
1. Open your AI assistant
2. **Attach/upload** the files mentioned at the top of the prompt (implementation_plan.md + module spec + any existing code files)
3. Paste the entire prompt
4. Let the AI generate all files
5. Review, test, commit

### Step 4: After All Modules Done
Run integration using `10_integration.md` prompt.

## Important Notes
- Each prompt tells the AI the **exact file paths** to create
- Each prompt includes the **data contracts** — what the module receives and what it outputs
- Each prompt includes **test requirements** — the AI must create and run tests
- **The Core module code must be available** in the workspace before running any other prompt (the AI needs to read it to use the correct classes/types)
