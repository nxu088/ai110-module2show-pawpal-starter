import streamlit as st
from datetime import datetime
from pawpal_system import Frequency, Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs (UI only)")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])

if "owner" not in st.session_state:
    st.session_state.owner = Owner(
        owner_id="o1",
        name=owner_name,
        email="",
        phone="",
    )
if "scheduler" not in st.session_state:
    st.session_state.scheduler = Scheduler()
if "task_counter" not in st.session_state:
    st.session_state.task_counter = 0

owner: Owner = st.session_state.owner
scheduler: Scheduler = st.session_state.scheduler

# --- Add a Pet ---
st.markdown("### Add a Pet")
if st.button("Add Pet"):
    pet_id = f"p{len(owner.get_pets()) + 1}"
    new_pet = Pet(pet_id=pet_id, name=pet_name, species=species, breed="", age=0)
    owner.add_pet(new_pet)
    st.success(f"Added {pet_name}!")

pets = owner.get_pets()
if pets:
    st.caption("Registered: " + ", ".join(p.name for p in pets))

# --- Schedule a Task ---
st.markdown("### Schedule a Task")
# st.caption("Add a few tasks. In your final version, these should feed into your scheduler.")

# # OLD placeholder — stored raw dicts, not connected to pawpal_system
# if "tasks" not in st.session_state:
#     st.session_state.tasks = []
# col1, col2, col3 = st.columns(3)
# with col1:
#     task_title = st.text_input("Task title", value="Morning walk")
# with col2:
#     duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
# with col3:
#     priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
# if st.button("Add task"):
#     st.session_state.tasks.append(
#         {"title": task_title, "duration_minutes": int(duration), "priority": priority}
#     )
# if st.session_state.tasks:
#     st.write("Current tasks:")
#     st.table(st.session_state.tasks)
# else:
#     st.info("No tasks yet. Add one above.")

if not pets:
    st.info("Add a pet above before scheduling tasks.")
else:
    col1, col2 = st.columns(2)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
        task_desc = st.text_input("Description", value="")
        selected_pet_name = st.selectbox("For pet", [p.name for p in pets])
    with col2:
        due_time = st.time_input("Due time", value=datetime.now().replace(second=0, microsecond=0).time())
        frequency = st.selectbox("Frequency", [f.value for f in Frequency])

    if st.button("Schedule Task"):
        target_pet = next(p for p in pets if p.name == selected_pet_name)
        st.session_state.task_counter += 1
        new_task = Task(
            task_id=f"t{st.session_state.task_counter}",
            title=task_title,
            description=task_desc,
            due_date=datetime.combine(datetime.today(), due_time),
            frequency=Frequency(frequency),
        )
        scheduler.schedule_task(new_task, target_pet)
        st.success(f"Scheduled '{task_title}' for {target_pet.name} at {due_time:%H:%M}.")

st.divider()

st.subheader("Today's Schedule")
# st.caption("This button should call your scheduling logic once you implement it.")

# # OLD placeholder — showed a warning and static instructions instead of real data
# if st.button("Generate schedule"):
#     st.warning("Not implemented yet. ...")

if st.button("Generate Schedule"):
    upcoming = owner.view_schedule(scheduler)
    overdue = [
        t for t in scheduler.get_overdue_tasks()
        if any(t in p.get_tasks() for p in owner.get_pets())
    ]

    if not upcoming and not overdue:
        st.info("No tasks scheduled yet.")

    if overdue:
        st.error(f"{len(overdue)} overdue task(s)")
        for task in overdue:
            st.write(f"⚠️ {task.due_date:%H:%M}  {task.title}")

    if upcoming:
        st.success(f"{len(upcoming)} upcoming task(s)")
        for task in upcoming:
            pet_label = next(p.name for p in owner.get_pets() if task in p.get_tasks())
            st.write(f"🕐 {task.due_date:%H:%M}  {task.title} ({pet_label}) — {task.description}")
