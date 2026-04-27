# PawPal+ Reflection

---

## Section 1: System Design

### Three Core Actions a User Should Be Able to Perform

1. **Add a pet** — the user should be able to register their pet with a name, species, and age so the app knows who to schedule tasks for
2. **Schedule a task** — the user should be able to assign an activity like a walk or feeding to a specific pet with a time and how often it repeats
3. **View today's schedule** — the user should be able to see all tasks sorted by time so they know what needs to be done and in what order

---

### 1a. Initial Design

I designed four main classes for this system:

**Task** — I chose this because every activity (walk, feeding, medication) is basically one task with a description, a time, a frequency, and a status. Using a dataclass kept it clean and easy to work with.

**Pet** — Each pet needs to hold its own information and its own list of tasks. I gave it `add_task()` and `get_tasks()` methods so it can manage its own data without anything reaching in from outside.

**Owner** — The owner is the top level. They own all the pets, so I gave them an `add_pet()` method and a way to collect all tasks across every pet with `get_all_tasks()`.

**Scheduler** — I made this a separate class because I did not want sorting or conflict logic mixed into the other classes. The Scheduler takes an Owner and does all the smart work on top of the data.

The main relationship is: Owner has many Pets, and each Pet has many Tasks. The Scheduler sits on top and uses the Owner to access everything.

---

### 1b. Design Changes

After thinking through the design more, I added a `reschedule()` method directly on the `Task` class instead of putting that logic in the Scheduler. It made more sense for a Task to know how to create its own next occurrence. The Scheduler just calls it when needed.

I also added a `get_pet_names()` method to Owner because the Streamlit UI needed a list of just the names for the dropdown selector. It was a small addition but it made the UI code a lot cleaner.

I also added a `priority` field to the Task class after realizing the UI needed a visual indicator and the Scheduler needed a secondary sort key when two tasks share the same time slot.

---

## Section 2: Algorithmic Layer

### 2a. Algorithms Implemented

**Sorting** — I used Python's `sorted()` function with a lambda key to sort tasks by their time string in `HH:MM` format. Since the format is consistent and zero-padded, string sorting works correctly for chronological order. Priority is used as a secondary sort key within the same time slot.

**Filtering** — I used list comprehensions to filter tasks by pet name or by completion status. It is simple but effective and keeps each filter to one readable line.

**Conflict Detection** — I used a nested loop to compare every pair of tasks. If two tasks share the same `pet_name` and the same `time`, a warning gets added to a list and returned to the UI. The app does not crash; it just shows the user a warning so they can fix it. Duplicate conflict warnings are deduplicated before rendering using a set.

**Recurring Tasks** — When `mark_task_complete()` is called on a daily or weekly task, the Scheduler calls `task.reschedule()` which returns a new Task with the time bumped forward using `timedelta`. That new task gets added to the correct pet's list automatically.

**RAG Retrieval** — The RAG pipeline uses `sentence-transformers` to embed both the source documents and the user's question into vectors. ChromaDB does cosine similarity search and returns the top 3 most relevant chunks. Those chunks are passed to GPT-3.5-turbo along with the question and an instruction to only answer from the provided context.

---

### 2b. Tradeoffs

The conflict detection only flags tasks that are scheduled at the exact same time. It does not catch overlapping durations. For example, if one task runs from 9:00 to 9:30 and another starts at 9:15, the system would not catch that overlap. I made this tradeoff because tasks do not have a duration field, so checking for overlap was not possible without redesigning the Task class. For a pet care app, exact time matching covers the cases that actually matter in practice.

The confidence threshold is set at 0.4. Answers below that level are flagged as low-confidence rather than silently passed through. This is more honest but it does mean some edge-case queries get an unnecessary warning. I tried 0.7 and it flagged too many legitimate answers. I tried 0.2 and it let too many weak answers through. 0.4 felt like the right balance after testing.

---

## Section 3: AI Strategy and Reflection

### Which Copilot features were most effective?

The most helpful thing was being able to describe what I wanted in plain English and get working code back quickly. When I needed to sort tasks by time, asking how to sort by a `HH:MM` time string using a lambda saved me a lot of time. Inline autocomplete was also useful for repetitive parts like list comprehensions and dataclass field definitions.

### One example of an AI suggestion I rejected or modified

When I first got the Scheduler skeleton, the AI put the rescheduling logic entirely inside the Scheduler class. I moved it into a `reschedule()` method on the Task class instead because it made more logical sense. A Task should know how to create its next occurrence. Keeping that logic in the Scheduler made it harder to read and harder to test independently.

A second example was the guardrail regex patterns. The AI suggested `\bno\s+vet\b` which was too broad and would have blocked legitimate advice like "no vet appointment needed for routine grooming." I rewrote it to a more specific pattern. This showed me that AI-generated safety logic always needs careful human review.

### How did using separate chat sessions help?

Keeping the design phase, implementation phase, and testing phase in separate sessions helped a lot. When everything was in one long session, the AI would sometimes reference earlier incomplete code and produce suggestions that were inconsistent with where the project had ended up. Starting fresh for each phase meant the AI was working with the current state of the project.

### What I learned about being the lead architect

The biggest thing I learned is that AI is good at writing code but it does not know what the system is supposed to feel like or how the pieces are supposed to fit together. It can produce something that technically works but is messy or does not match the actual design intent. My job was to read what came back, decide if it made sense for the system, and change it when it did not. The rescheduling decision, the confidence threshold, the key uniqueness fix in Streamlit — all of those required understanding the whole project well enough to see what was wrong. AI made each individual piece faster to produce. It could not make the decisions about how everything fits.