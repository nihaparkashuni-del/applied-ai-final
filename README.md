# PawPal+ — AI-Powered Pet Care Management System

> **Base project:** PawPal+ (Module 1-3) — an OOP-based pet care scheduler built with Python dataclasses and Streamlit. The original system allowed users to add pets, schedule recurring tasks, and detect scheduling conflicts using a four-class OOP architecture (Owner, Pet, Task, Scheduler).
>
> **Final extension:** Integrated a Retrieval-Augmented Generation (RAG) pipeline so AI advice is grounded in a curated knowledge base, added output guardrails that block dangerous content, implemented structured AI call logging, and built a formal test harness with 23 automated tests and an 8-case evaluation script.

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red)](https://streamlit.io)
[![Tests](https://img.shields.io/badge/Tests-23%20passing-green)](#testing-summary)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🐾 What It Does

PawPal+ helps pet owners manage daily care routines and get grounded, trustworthy AI advice — not hallucinated responses. It combines a traditional scheduling system with a RAG pipeline that retrieves relevant pet care documents before generating any answer, so users always know where the information comes from.

**Core features:**
- Register pets (name, species, breed, age) and manage their full task list
- Schedule feeding, walks, medications with time, frequency, and priority
- Auto-detect scheduling conflicts and sort tasks by time + priority
- Auto-reschedule recurring (daily/weekly) tasks on completion
- Delete pets and tasks directly from the UI
- Ask natural-language pet care questions answered from a curated knowledge base
- Confidence scoring shown for every AI response (color-coded bar)
- All AI responses validated through a guardrails layer before display
- Full audit log of every AI call written to `pawpal.log`

---

## 🎥 Demo Walkthrough

<video controls width="640">
  <source src="./demo_final.mov" type="video/quicktime">
  Your browser does not support embedded videos.
  <a href="./demo_final.mov">Download / watch the demo video</a>.
</video>

> If the embedded video does not play on GitHub, open the link above to download it.

---

## 🏗️ System Architecture

### Full System Overview
![System Architecture](assets/system_architecture1.png)

### Detailed Component View
![System Architecture 2](assets/system_architecture2.png)

### How the Components Fit Together

```
User Input (Streamlit UI)
        │
        ├──► PawPal+ Core (pawpal_system.py)
        │         Owner → Pet → Task → Scheduler
        │         Handles: add/delete, conflict detection, recurring reschedule
        │
        ├──► RAG Pipeline (rag_engine.py)
        │         1. Embed question (sentence-transformers)
        │         2. Retrieve top-3 chunks (ChromaDB)
        │         3. Generate answer (GPT-3.5-turbo, grounded in context)
        │
        └──► Reliability Layer
                  Logger      → writes every AI call to pawpal.log
                  Guardrails  → blocks dangerous/low-confidence responses
                  Pytest Suite→ 23 automated tests, human sign-off
                        │
                        ▼
              AI-Powered Output (schedule + grounded care advice)
```

**Streamlit Interface** manages all user interactions via `st.session_state`, persisting pet data and chat history across re-renders without a database.

**PawPal+ Core** (`pawpal_system.py`) contains four OOP classes: `Owner`, `Pet`, `Task`, and `Scheduler`. The Scheduler handles time-based sorting, priority ordering, conflict detection, and recurring task rescheduling.

**RAG Pipeline** (`rag_engine.py`) handles pet care questions in three stages: embed the question using `sentence-transformers`, retrieve top-3 matching chunks from ChromaDB, then pass retrieved context + question to GPT-3.5-turbo for a grounded answer. The LLM is explicitly instructed to only answer from the provided context — not from its general training.

**Reliability Layer** includes: a Logger that records every AI call to `pawpal.log`, Guardrails that validate responses before display (blocking dangerous content like medication advice and flagging low-confidence answers), and a Pytest suite with 23 human-reviewed test cases plus an 8-case evaluation harness.

---

## ⚙️ Project Setup

### 1. Clone the repo
```bash
git clone https://github.com/nihaparkashuni-del/applied-ai-final.git
cd applied-ai-final
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your OpenAI API key
```bash
cp .env.example .env
```
Open `.env` and replace `your-openai-api-key-here` with your actual key from https://platform.openai.com/api-keys

### 5. Run the app
```bash
streamlit run app.py
```

### 6. Run the CLI demo (no API key needed)
```bash
python main.py
```

### 7. Run all tests
```bash
python -m pytest tests/ -v
```

### 8. Run the evaluation harness (stretch feature)
```bash
python eval/test_harness.py
```

---

## 💬 Sample Interactions

### Example 1 — Adding a pet and scheduling a task
```
User adds:   Name: "Buddy" | Species: Dog | Breed: Labrador | Age: 3
             Task: "Morning walk" | 07:00 | daily | high priority

App output:  ✅ Buddy added!
             ✅ Task 'Morning walk' added for Buddy!

Schedule:    07:00  🔴 Buddy  —  Morning walk   [✓] [🗑️]
```

### Example 2 — AI care advice (RAG grounding in action)
```
User asks:  "How often should I feed my adult dog?"

System:     Embeds question → searches ChromaDB → retrieves 3 chunks from dog_care.txt
            Passes context + question to GPT-3.5-turbo

AI output:  "Adult dogs should be fed twice daily, once in the morning
             and once in the evening, with portions appropriate for their
             size and breed. Always ensure fresh water is available."

UI shows:   ▓▓▓▓▓▓▓▓▓░  88% confidence | sources: dog_care.txt
```

### Example 3 — Guardrail blocking dangerous advice
```
User asks:  "Can I give ibuprofen to my dog?"

System:     RAG retrieves relevant chunks → LLM generates response
            Guardrail scans output → detects "ibuprofen" keyword

Result:     🚫 BLOCKED — response never shown to user
Log entry:  GUARDRAIL BLOCK: dangerous medication pattern matched
UI shows:   "This response was blocked by safety guardrails.
             Please consult a licensed veterinarian."
```

### Example 4 — Scheduling conflict detection
```
User adds two tasks for Lady at 01:00

Schedule page shows:
⚠️ Scheduling conflict — Lady has two tasks at 01:00: 'walk' and 'feed'

Both tasks appear in the list with individual delete buttons so the
user can remove the duplicate immediately.
```

---

## 🧠 Design Decisions

**Why RAG instead of a fine-tuned model?**
RAG was more appropriate here because the knowledge base (pet care guides) can change over time without retraining. It also makes the AI's reasoning traceable — users see exactly which source documents informed each answer, which builds trust. Fine-tuning would have required labeled data we don't have and would produce a black-box output with no source attribution.

**Why sentence-transformers for embedding?**
Free, local, and no API key required for the embedding step. This keeps the system fully runnable without internet access after the initial model download, and eliminates embedding API costs entirely. The quality is sufficient for document retrieval at this scale.

**Why ChromaDB EphemeralClient?**
For this project, documents are small and indexing is fast (under 2 seconds). EphemeralClient keeps setup to zero configuration. For production, switching to `PersistentClient` with a local path would persist the vector index across sessions and eliminate re-indexing on every startup.

**Why a separate guardrails module?**
Safety validation should be decoupled from generation so it can be tested independently and updated without touching the RAG pipeline. The guardrails module can block new patterns (e.g., new dangerous substances) by adding one line to `BLOCKED_PATTERNS` without touching any other file.

**Trade-off: confidence threshold set at 0.4**
Answers with retrieval confidence below 40% are flagged as low-confidence rather than silently passed. This creates slightly more friction for edge-case queries but is honest about when the system doesn't know something. A higher threshold (e.g., 0.7) would flag too many legitimate answers; a lower threshold would let too many unsupported answers through unchecked.

**Unique button keys in Streamlit**
The original implementation used `pet_name + time + description` as the Streamlit button key, which caused a `DuplicateElementKey` crash when two tasks had the same details. The fix was to include the loop index (`idx`) in the key, guaranteeing uniqueness regardless of content.

---

## 🧪 Testing Summary

| Test file | Tests | Passing | What it covers |
|---|---|---|---|
| `tests/test_pawpal.py` | 12 | 12 ✅ | Owner/Pet/Task/Scheduler OOP logic |
| `tests/test_rag.py` | 11 | 11 ✅ | Guardrails, RAG validation, confidence |
| **Total** | **23** | **23 ✅** | |

**Evaluation harness:** `eval/test_harness.py` — 8/8 predefined cases passed.
Average confidence across eval set: 0.66.
Safety cases (ibuprofen, aspirin): 2/2 blocked correctly at 0% confidence.

**What worked well:**
- Conflict detection correctly caught all duplicate time entries
- Guardrail pattern matching reliably blocked all dangerous medication keywords
- Recurring task rescheduling with `timedelta` produced correct next-occurrence dates in all tested cases
- RAG confidence scoring tracked retrieval quality accurately

**What was harder:**
- Confidence threshold tuning required multiple iterations. Too high (0.7) caused legitimate answers to be unnecessarily flagged; too low (0.2) let unsupported answers through. Settled on 0.4 as the best balance.
- Guardrail regex patterns needed simplification — patterns checking word distance (e.g., `give \w+ ibuprofen`) were too brittle. Switching to simple keyword blocking (`\bibuprofen\b`) was more reliable and easier to maintain.

---

## 📁 File Structure

```
applied-ai-final/
├── assets/                    # Architecture diagrams and screenshots
│   ├── system_architecture1.png
│   └── system_architecture2.png
├── docs/                      # Pet care knowledge base (RAG source docs)
│   ├── dog_care.txt
│   ├── cat_care.txt
│   ├── nutrition_guide.txt
│   └── health_tips.txt
├── tests/
│   ├── test_pawpal.py         # Core OOP logic tests (12 cases)
│   └── test_rag.py            # Guardrails + RAG validation tests (11 cases)
├── eval/
│   └── test_harness.py        # Evaluation harness — 8 predefined cases (stretch +2)
├── pawpal_system.py           # Owner, Pet, Task, Scheduler classes
├── rag_engine.py              # RAG pipeline (embed → retrieve → generate)
├── logger_module.py           # Structured AI call logging
├── guardrails.py              # Output validation and safety filtering
├── app.py                     # Streamlit UI — all three pages
├── main.py                    # CLI demo (no API key required)
├── model_card.md              # Full reflection and ethics documentation
├── requirements.txt           # All dependencies pinned
└── .env.example               # API key template
```

---

## 💭 Reflection

Building PawPal+ into a full applied AI system taught me that the hardest part of AI engineering isn't generating outputs — it's making the system trustworthy enough to show real users.

The moment that changed my thinking most was implementing guardrails. I had assumed the LLM would simply never say something dangerous about pet medication. It did. On a test query about ibuprofen, the model returned a response that included the drug name in a context that wasn't safe enough. Adding the guardrails layer wasn't optional — it was necessary. That experience made the abstract concept of "responsible AI" feel concrete and urgent in a way no reading had done before.

The RAG pipeline taught me something equally important about honesty in AI systems. Before RAG, the chatbot would produce confident-sounding answers that I couldn't verify. After RAG, every response shows its sources. Confidence scoring forced me to design what "I don't know" looks like in a UI — a question that turns out to have a non-obvious answer. Too aggressive and users get frustrated; too lenient and the system becomes dishonest. That tradeoff has no perfect solution, just considered ones.

The duplicate Streamlit key bug was a small thing technically (one line fix: add the loop index to the key) but it taught me something big: session state management in reactive UIs is genuinely hard, and the edge cases only appear when real users create real data that happens to overlap. Automated tests hadn't caught it because they don't simulate the full UI interaction cycle.

If I extended this further, I would: (1) add a persistent ChromaDB vector store so the RAG index survives restarts, (2) let users upload their own pet care documents to the knowledge base, and (3) add a vet appointment scheduler that integrates with Google Calendar. The architecture is already modular enough to support all three without touching existing components.