"""
PawPal+ — AI-Powered Pet Care Management System
Full Streamlit UI with RAG-enhanced care advice.

Enhancements:
- Health log per pet (track symptoms and vet visits)
- AI task suggestions based on species and age
- Upcoming tasks reminder badge in sidebar

Run with:  streamlit run app.py
"""

import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

from pawpal_system import Owner, Pet, Task, Scheduler
from rag_engine import RAGEngine
from guardrails import validate_response
from logger_module import setup_logger, log_ai_call, log_error

load_dotenv()
pawpal_logger = setup_logger()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PawPal+",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state init ────────────────────────────────────────────────────────
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="My Account")

if "rag" not in st.session_state:
    try:
        st.session_state.rag = RAGEngine(docs_folder="docs")
        pawpal_logger.info("RAGEngine loaded successfully.")
    except Exception as exc:
        st.session_state.rag = None
        log_error("Failed to initialize RAGEngine", exc, pawpal_logger)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "health_log" not in st.session_state:
    st.session_state.health_log = {}

owner: Owner = st.session_state.owner
rag: RAGEngine = st.session_state.rag

# ── Upcoming tasks helper (next 2 hours) ─────────────────────────────────────
def get_upcoming_tasks(owner, minutes_ahead=120):
    now = datetime.now()
    upcoming = []
    for pet in owner.pets:
        for task in pet.tasks:
            try:
                task_dt = datetime.strptime(task.time, "%H:%M").replace(
                    year=now.year, month=now.month, day=now.day
                )
                diff = (task_dt - now).total_seconds() / 60
                if 0 <= diff <= minutes_ahead:
                    upcoming.append((task, round(diff)))
            except Exception:
                pass
    return sorted(upcoming, key=lambda x: x[1])

# ── AI task suggestions by species and age ───────────────────────────────────
SPECIES_SUGGESTIONS = {
    "Dog": [
        ("Morning walk", "07:00", "daily", "high"),
        ("Evening walk", "18:00", "daily", "high"),
        ("Feeding", "08:00", "daily", "high"),
        ("Feeding", "17:00", "daily", "high"),
        ("Teeth brushing", "20:00", "weekly", "medium"),
        ("Bath", "10:00", "weekly", "low"),
    ],
    "Cat": [
        ("Feeding", "08:00", "daily", "high"),
        ("Feeding", "18:00", "daily", "high"),
        ("Litter box cleaning", "09:00", "daily", "high"),
        ("Playtime", "19:00", "daily", "medium"),
        ("Brush coat", "10:00", "weekly", "low"),
    ],
    "Bird": [
        ("Feeding", "08:00", "daily", "high"),
        ("Fresh water", "08:00", "daily", "high"),
        ("Cage cleaning", "09:00", "weekly", "medium"),
        ("Playtime / out of cage", "17:00", "daily", "medium"),
    ],
    "Rabbit": [
        ("Feeding (hay)", "08:00", "daily", "high"),
        ("Fresh vegetables", "12:00", "daily", "medium"),
        ("Water change", "08:00", "daily", "high"),
        ("Cage cleaning", "09:00", "weekly", "medium"),
    ],
    "Other": [
        ("Feeding", "08:00", "daily", "high"),
        ("Fresh water", "08:00", "daily", "high"),
        ("Health check", "10:00", "weekly", "medium"),
    ],
}

def get_age_extra_tasks(species, age):
    extras = []
    if species == "Dog":
        if age < 1:
            extras.append(("Puppy training session", "16:00", "daily", "high"))
            extras.append(("Vaccination check", "09:00", "once", "high"))
        elif age >= 8:
            extras.append(("Senior health check", "10:00", "weekly", "high"))
            extras.append(("Joint supplement", "08:00", "daily", "medium"))
    if species == "Cat":
        if age < 1:
            extras.append(("Kitten socialization play", "15:00", "daily", "medium"))
        elif age >= 10:
            extras.append(("Senior vet checkup", "10:00", "weekly", "high"))
    return extras

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🐾 PawPal+")
    st.caption("AI-Powered Pet Care Manager")
    st.divider()

    page = st.radio(
        "Navigate",
        ["📋 Schedule", "➕ Add Pet / Task", "🏥 Health Log", "🤖 AI Care Advice"],
        label_visibility="collapsed",
    )

    st.divider()
    st.metric("Pets registered", len(owner.pets))

    upcoming = get_upcoming_tasks(owner)
    pending_count = len(owner.get_all_pending_tasks())
    st.metric("Pending tasks", pending_count)

    if upcoming:
        st.warning(f"⏰ **{len(upcoming)} task(s) due soon**")
        for task, mins in upcoming[:3]:
            st.caption(f"• {task.pet_name}: {task.description} in {mins} min")

    if rag is None:
        st.warning("RAG offline — check OPENAI_API_KEY in .env")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1: SCHEDULE
# ═══════════════════════════════════════════════════════════════════════════════
if page == "📋 Schedule":
    st.header("📋 Today's Schedule")

    if not owner.pets:
        st.info("No pets added yet. Go to **Add Pet / Task** to get started.")
    else:
        scheduler = Scheduler(owner)
        schedule = scheduler.get_todays_schedule()
        conflicts = scheduler.detect_conflicts()

        seen_conflicts = set()
        if conflicts:
            for task_a, task_b in conflicts:
                conflict_key = tuple(sorted([
                    f"{task_a.pet_name}_{task_a.time}_{task_a.description}",
                    f"{task_b.pet_name}_{task_b.time}_{task_b.description}",
                ]))
                if conflict_key not in seen_conflicts:
                    seen_conflicts.add(conflict_key)
                    st.warning(
                        f"Scheduling conflict: {task_a.pet_name} has two tasks at "
                        f"**{task_a.time}**: '{task_a.description}' and '{task_b.description}'"
                    )

        if not schedule:
            st.success("All tasks complete for today!")
        else:
            priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}

            hcols = st.columns([1, 2, 3, 1, 1])
            hcols[0].markdown("**Time**")
            hcols[1].markdown("**Pet**")
            hcols[2].markdown("**Task**")
            hcols[3].markdown("**Done**")
            hcols[4].markdown("**Delete**")
            st.divider()

            for idx, task in enumerate(schedule):
                cols = st.columns([1, 2, 3, 1, 1])
                cols[0].write(f"**{task.time}**")
                cols[1].write(f"{priority_color.get(task.priority, '⚪')} {task.pet_name}")
                cols[2].write(task.description)

                if cols[3].button("✓", key=f"done_{idx}_{task.pet_name}_{task.time}"):
                    scheduler.mark_task_complete(task.pet_name, task.description)
                    pawpal_logger.info("UI: Task '%s' for %s marked done.", task.description, task.pet_name)
                    st.rerun()

                if cols[4].button("🗑️", key=f"del_{idx}_{task.pet_name}_{task.time}"):
                    for pet in owner.pets:
                        if pet.name == task.pet_name:
                            pet.tasks = [
                                t for t in pet.tasks
                                if not (t.description == task.description and t.time == task.time)
                            ]
                            break
                    pawpal_logger.info("UI: Task '%s' for %s deleted.", task.description, task.pet_name)
                    st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2: ADD PET / TASK
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "➕ Add Pet / Task":
    st.header("➕ Add Pet / Task")
    col_pet, col_task = st.columns(2)

    with col_pet:
        st.subheader("Add a New Pet")
        with st.container(border=True):
            pet_name = st.text_input("Pet name", key="pet_name_input")
            species = st.selectbox("Species", ["Dog", "Cat", "Bird", "Rabbit", "Other"])
            breed = st.text_input("Breed", key="breed_input")
            age = st.number_input("Age (years)", min_value=0, max_value=30, value=1)

            if st.button("Add Pet", use_container_width=True, type="primary"):
                if pet_name.strip():
                    new_pet = Pet(
                        name=pet_name.strip(),
                        species=species,
                        breed=breed.strip() or "Unknown",
                        age=int(age),
                    )
                    owner.add_pet(new_pet)
                    st.success(f"✅ **{pet_name}** added!")
                    st.rerun()
                else:
                    st.error("Please enter a pet name.")

        if owner.pets:
            st.subheader("Your Pets")
            for pidx, pet in enumerate(owner.pets):
                pcols = st.columns([3, 1])
                pcols[0].write(f"**{pet.name}** — {pet.species}, {pet.age} yr")
                if pcols[1].button("🗑️", key=f"del_pet_{pidx}_{pet.name}"):
                    owner.pets = [p for p in owner.pets if p.name != pet.name]
                    pawpal_logger.info("UI: Pet '%s' deleted.", pet.name)
                    st.rerun()

    with col_task:
        st.subheader("Add a Task")
        with st.container(border=True):
            if not owner.pets:
                st.info("Add a pet first.")
            else:
                task_pet = st.selectbox("For which pet?", [p.name for p in owner.pets])
                task_desc = st.text_input("Task description (e.g., Morning walk)")
                task_time = st.time_input("Scheduled time")
                task_freq = st.selectbox("Frequency", ["once", "daily", "weekly"])
                task_priority = st.select_slider(
                    "Priority", options=["low", "medium", "high"], value="medium"
                )

                if st.button("Add Task", use_container_width=True, type="primary"):
                    if task_desc.strip():
                        new_task = Task(
                            description=task_desc.strip(),
                            time=task_time.strftime("%H:%M"),
                            frequency=task_freq,
                            pet_name=task_pet,
                            priority=task_priority,
                        )
                        for pet in owner.pets:
                            if pet.name == task_pet:
                                pet.add_task(new_task)
                                break
                        st.success(f"✅ Task '**{task_desc}**' added for {task_pet}!")
                        st.rerun()
                    else:
                        st.error("Please enter a task description.")

        # AI suggestions
        if owner.pets:
            st.divider()
            st.subheader("🤖 AI Task Suggestions")
            suggest_pet_name = st.selectbox(
                "Get suggestions for:", [p.name for p in owner.pets], key="suggest_pet"
            )
            suggest_pet = next((p for p in owner.pets if p.name == suggest_pet_name), None)

            if suggest_pet:
                base = SPECIES_SUGGESTIONS.get(suggest_pet.species, SPECIES_SUGGESTIONS["Other"])
                extras = get_age_extra_tasks(suggest_pet.species, suggest_pet.age)
                all_suggestions = base + extras
                st.caption(
                    f"Recommended tasks for a {suggest_pet.age}-year-old "
                    f"{suggest_pet.species.lower()} ({suggest_pet.breed}):"
                )
                for sidx, (desc, time, freq, priority) in enumerate(all_suggestions):
                    scols = st.columns([3, 1])
                    scols[0].write(f"**{desc}** — {time} ({freq}, {priority})")
                    if scols[1].button("Add", key=f"sugg_{sidx}_{suggest_pet_name}_{desc}"):
                        new_task = Task(
                            description=desc,
                            time=time,
                            frequency=freq,
                            pet_name=suggest_pet_name,
                            priority=priority,
                        )
                        suggest_pet.add_task(new_task)
                        st.success(f"✅ Added '{desc}' for {suggest_pet_name}!")
                        pawpal_logger.info("UI: AI-suggested task '%s' added for %s.", desc, suggest_pet_name)
                        st.rerun()

        # View/delete tasks
        if owner.pets:
            st.divider()
            selected_pet_name = st.selectbox(
                "View/delete tasks for:", [p.name for p in owner.pets], key="view_tasks_pet"
            )
            selected_pet = next((p for p in owner.pets if p.name == selected_pet_name), None)
            if selected_pet and selected_pet.tasks:
                st.subheader(f"Tasks for {selected_pet_name}")
                for tidx, task in enumerate(selected_pet.tasks):
                    tcols = st.columns([3, 1])
                    status = "✅" if getattr(task, "status", "pending") == "done" else "⏳"
                    tcols[0].write(f"{status} **{task.time}** — {task.description} ({task.priority})")
                    if tcols[1].button("🗑️", key=f"del_task_{tidx}_{selected_pet_name}_{task.time}_{task.description[:5]}"):
                        selected_pet.tasks = [
                            t for t in selected_pet.tasks
                            if not (t.description == task.description and t.time == task.time)
                        ]
                        pawpal_logger.info("UI: Task '%s' for %s deleted.", task.description, selected_pet_name)
                        st.rerun()
            elif selected_pet:
                st.info(f"No tasks yet for {selected_pet_name}.")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3: HEALTH LOG
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🏥 Health Log":
    st.header("🏥 Health Log")
    st.caption("Track symptoms, vet visits, medications, and observations for each pet.")

    if not owner.pets:
        st.info("Add a pet first to start logging health records.")
    else:
        selected_pet_name = st.selectbox(
            "Select pet:", [p.name for p in owner.pets], key="health_pet"
        )

        if selected_pet_name not in st.session_state.health_log:
            st.session_state.health_log[selected_pet_name] = []

        log = st.session_state.health_log[selected_pet_name]

        with st.container(border=True):
            st.subheader(f"Add Entry for {selected_pet_name}")
            entry_cols = st.columns([2, 2])
            entry_type = entry_cols[0].selectbox(
                "Entry type",
                ["Symptom", "Vet Visit", "Medication", "Vaccination", "General Observation"],
                key="entry_type",
            )
            entry_date = entry_cols[1].date_input("Date", value=datetime.today(), key="entry_date")
            entry_note = st.text_area("Notes", key="entry_note")

            if st.button("Save Entry", type="primary"):
                if entry_note.strip():
                    log.append({
                        "date": entry_date.strftime("%Y-%m-%d"),
                        "type": entry_type,
                        "note": entry_note.strip(),
                    })
                    st.session_state.health_log[selected_pet_name] = log
                    pawpal_logger.info("Health log: '%s' entry added for %s.", entry_type, selected_pet_name)
                    st.success(f"✅ Entry saved for {selected_pet_name}!")
                    st.rerun()
                else:
                    st.error("Please add a note before saving.")

        st.divider()

        type_icons = {
            "Symptom": "🤒",
            "Vet Visit": "🏥",
            "Medication": "💊",
            "Vaccination": "💉",
            "General Observation": "📝",
        }

        if log:
            st.subheader(f"Health History — {selected_pet_name}")
            for eidx, entry in enumerate(reversed(log)):
                real_idx = len(log) - 1 - eidx
                ecols = st.columns([4, 1])
                icon = type_icons.get(entry["type"], "📋")
                ecols[0].markdown(f"{icon} **{entry['type']}** — {entry['date']}\n\n{entry['note']}")
                if ecols[1].button("🗑️", key=f"del_health_{selected_pet_name}_{eidx}"):
                    log.pop(real_idx)
                    st.session_state.health_log[selected_pet_name] = log
                    st.rerun()
                st.divider()
        else:
            st.info(f"No health entries yet for {selected_pet_name}.")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4: AI CARE ADVICE (RAG)
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 AI Care Advice":
    st.header("🤖 AI Pet Care Advisor")
    st.caption("Answers are grounded in a pet care knowledge base using Retrieval-Augmented Generation (RAG).")

    if rag is None:
        st.error("RAG engine failed to start. Check that OPENAI_API_KEY is set in your .env file.")
        st.info("Make sure your .env file contains: OPENAI_API_KEY=sk-proj-...")
    else:
        pet_context = ""
        if owner.pets:
            selected = st.selectbox(
                "Ask about which pet? (optional)",
                ["General"] + [p.name for p in owner.pets],
            )
            if selected != "General":
                pet = next(p for p in owner.pets if p.name == selected)
                pet_context = f"{pet.name} is a {pet.age}-year-old {pet.species} ({pet.breed})."
                pet_log = st.session_state.health_log.get(selected, [])
                if pet_log:
                    recent = pet_log[-3:]
                    log_summary = " | ".join(
                        [f"{e['type']} on {e['date']}: {e['note'][:80]}" for e in recent]
                    )
                    pet_context += f" Recent health notes: {log_summary}"

        st.divider()

        for entry in st.session_state.chat_history:
            with st.chat_message("user"):
                st.write(entry["question"])
            with st.chat_message("assistant"):
                st.markdown(entry["answer"])
                conf = entry.get("confidence", 0)
                bar = "▓" * int(conf * 10) + "░" * (10 - int(conf * 10))
                color = "green" if conf >= 0.8 else ("orange" if conf >= 0.4 else "red")
                srcs = ", ".join(entry.get("sources", [])) or "none"
                st.caption(f":{color}[{bar}] {conf:.0%} confidence | sources: {srcs}")

        question = st.chat_input("Ask a pet care question...")
        if question:
            with st.spinner("Searching knowledge base and generating answer..."):
                try:
                    raw = rag.generate_advice(query=question, pet_context=pet_context)
                    log_ai_call(question, raw, pawpal_logger)
                    is_valid, status, validated = validate_response(raw)

                    if not is_valid:
                        st.error(f"Guardrail blocked: {status}")
                        pawpal_logger.warning("Guardrail blocked response for query: '%s'", question)
                    else:
                        st.session_state.chat_history.append({
                            "question": question,
                            "answer": validated["answer"],
                            "confidence": validated["confidence"],
                            "sources": validated.get("sources_used", []),
                        })
                        st.rerun()
                except Exception as e:
                    err_msg = str(e)
                    if "401" in err_msg or "api_key" in err_msg.lower() or "invalid" in err_msg.lower():
                        st.error("Invalid API Key. Check your .env file. Get a key at https://platform.openai.com/api-keys")
                    elif "429" in err_msg:
                        st.error("Quota exceeded. Add credits at https://platform.openai.com/settings/billing")
                    else:
                        st.error(f"Error: {err_msg}")
                    log_error("AI advice generation failed", e, pawpal_logger)

        if st.session_state.chat_history:
            if st.button("Clear chat history"):
                st.session_state.chat_history = []
                st.rerun()