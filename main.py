from datetime import datetime, timedelta
from pawpal_system import Frequency, Owner, Pet, Scheduler, Task, preview_recurring

DIV = "-" * 44

def section(title: str) -> None:
    print(f"\n{DIV}\n  {title}\n{DIV}")

# --- Setup ---
owner = Owner(
    owner_id="o1",
    name="Alex Johnson",
    email="alex@example.com",
    phone="555-0100",
)

buddy    = Pet(pet_id="p1", name="Buddy",    species="Dog", breed="Labrador", age=3)
whiskers = Pet(pet_id="p2", name="Whiskers", species="Cat", breed="Siamese",  age=5)

owner.add_pet(buddy)
owner.add_pet(whiskers)

scheduler = Scheduler()

now = datetime.now().replace(second=0, microsecond=0)

# Tasks added intentionally out of chronological order
# to prove sort_by_time() reorders them correctly.
scheduler.schedule_task(
    Task("t4", "Vet Check-up", "Annual wellness exam",
         due_date=now.replace(hour=14, minute=0),
         frequency=Frequency.ONCE, priority="high", duration_minutes=60),
    whiskers,
)
scheduler.schedule_task(
    Task("t2", "Flea Treatment", "Apply monthly flea drops",
         due_date=now.replace(hour=10, minute=30),
         frequency=Frequency.MONTHLY, priority="medium", duration_minutes=15),
    buddy,
)
scheduler.schedule_task(
    Task("t5", "Playtime", "Laser pointer session",
         due_date=now.replace(hour=9, minute=0),
         frequency=Frequency.DAILY, priority="low", duration_minutes=20),
    whiskers,
)
scheduler.schedule_task(
    Task("t1", "Morning Walk", "30-min walk around the park",
         due_date=now.replace(hour=7, minute=0),
         frequency=Frequency.DAILY, priority="high", duration_minutes=30),
    buddy,
)
scheduler.schedule_task(
    Task("t6", "Grooming", "Brush coat",
         due_date=now.replace(hour=9, minute=0),   # same time as Playtime — tests tie-break
         frequency=Frequency.WEEKLY, priority="high", duration_minutes=25),
    buddy,
)
scheduler.schedule_task(
    Task("t3", "Feeding", "Wet food — half a can",
         due_date=now.replace(hour=8, minute=0),
         frequency=Frequency.DAILY, priority="high", duration_minutes=10),
    whiskers,
)

# ── Lambda sort key for "HH:MM" strings ─────────────────────────────────────
section("Lambda sort key: sorting HH:MM time strings")

time_strings = ["09:30", "07:00", "14:15", "08:00", "09:00"]

# Problem: plain alphabetical sort works accidentally for these, but breaks
# the moment hours have different digit counts (e.g. "9:00" vs "14:00").
# A lambda key makes the intent explicit and handles any formatting.

# Key idea: split "HH:MM" into (hours, minutes) as integers, return a tuple.
# sorted() compares tuples element-by-element: hours first, minutes as tiebreak.
by_time = sorted(time_strings, key=lambda s: (int(s.split(":")[0]),
                                               int(s.split(":")[1])))
print("  Unsorted:", time_strings)
print("  Sorted:  ", by_time)

# Reverse (latest first)
by_time_desc = sorted(time_strings, key=lambda s: (int(s.split(":")[0]),
                                                    int(s.split(":")[1])),
                      reverse=True)
print("  Reversed:", by_time_desc)

# The same lambda works on a list of task-like dicts
tasks_raw = [
    {"title": "Vet",          "time": "14:00"},
    {"title": "Morning Walk", "time": "07:00"},
    {"title": "Grooming",     "time": "09:00"},
    {"title": "Feeding",      "time": "07:30"},  # same hour as Walk — minute breaks tie
]
print()
print("  Sorting task dicts by 'time' field:")
for t in sorted(tasks_raw, key=lambda d: (int(d["time"].split(":")[0]),
                                           int(d["time"].split(":")[1]))):
    print(f"    {t['time']}  {t['title']}")

# How this connects to pawpal_system:
# sort_by_time() uses task.due_date (a datetime object) instead of a string,
# so the key becomes: lambda t: (t.due_date, priority_rank)
# — same idea, richer object as the source.

# ── timedelta walkthrough ────────────────────────────────────────────────────
# timedelta represents a fixed duration. Adding it to a datetime shifts the
# date forward by exactly that amount — no calendar edge-case math needed.
section("timedelta: how next due dates are calculated")

base = now.replace(hour=8, minute=0)   # pretend a task is due at 08:00 today

daily_delta   = timedelta(days=1)
weekly_delta  = timedelta(weeks=1)
monthly_delta = timedelta(days=30)

print(f"  Original due date  : {base:%Y-%m-%d %H:%M}")
print(f"  + timedelta(days=1): {base + daily_delta:%Y-%m-%d %H:%M}  <-- daily next")
print(f"  + timedelta(weeks=1): {base + weekly_delta:%Y-%m-%d %H:%M}  <-- weekly next")
print(f"  + timedelta(days=30): {base + monthly_delta:%Y-%m-%d %H:%M}  <-- monthly next")

# The scheduler uses exactly this formula inside _auto_reschedule:
#   next_task.due_date = task.due_date + _FREQUENCY_DELTA[task.frequency]
print()
print("  Chaining multiple days forward (what preview_recurring does):")
for i in range(1, 4):
    print(f"    day +{i}: {base + timedelta(days=i):%Y-%m-%d %H:%M}")

# ── Conflict detection ───────────────────────────────────────────────────────
# Run BEFORE any complete() calls so tasks are still active and detectable.

section("D. check_conflict — same-pet overlap (returns warning, no crash)")

# Buddy has Morning Walk 07:00-07:30. This task starts at 07:15 — overlaps.
late_walk = Task("cx1", "Agility Training", "Obstacle course",
                 due_date=now.replace(hour=7, minute=15),
                 frequency=Frequency.ONCE, priority="medium", duration_minutes=30)
msg = scheduler.check_conflict(late_walk, buddy)
print(f"  {msg if msg else 'No conflict'}")

# No overlap — starts after walk ends (07:30)
clear_task = Task("cx2", "Nail Trim", "Clip front paws",
                  due_date=now.replace(hour=7, minute=30),
                  frequency=Frequency.ONCE, priority="low", duration_minutes=10)
msg = scheduler.check_conflict(clear_task, buddy)
print(f"  {msg if msg else 'No conflict — safe to schedule Nail Trim at 07:30'}")

section("E. check_conflict — cross-pet overlap (owner can only be in one place)")
# Whiskers has Feeding 08:00-08:10. This Buddy task runs 08:05 — owner conflict.
buddy_overlap = Task("cx3", "Buddy Breakfast", "Fill food bowl",
                     due_date=now.replace(hour=8, minute=5),
                     frequency=Frequency.ONCE, priority="high", duration_minutes=15)
msg = scheduler.check_conflict(buddy_overlap, buddy)
print(f"  {msg if msg else 'No conflict'}")

section("F. get_all_conflicts — full schedule audit (all overlapping pairs)")
# Add two tasks that intentionally collide to populate the audit
scheduler.schedule_task(
    Task("cx4", "Evening Walk", "Quick loop around block",
         due_date=now.replace(hour=10, minute=20),
         frequency=Frequency.ONCE, priority="medium", duration_minutes=30),
    buddy,
)
scheduler.schedule_task(
    Task("cx5", "Bath Time", "Shampoo and rinse",
         due_date=now.replace(hour=10, minute=25),
         frequency=Frequency.ONCE, priority="low", duration_minutes=20),
    whiskers,
)
conflicts = scheduler.get_all_conflicts()
if conflicts:
    for c in conflicts:
        print(f"  {c}")
else:
    print("  No conflicts found.")

# ── Recurring auto-reschedule demo ──────────────────────────────────────────
# PATH A: call task.complete() directly — callback fires automatically
section("A. task.complete() directly — daily Feeding (Whiskers)")
feeding = next(t for t in whiskers.get_tasks() if t.task_id == "t3")
print(f"  Before: {len(scheduler.filter_tasks(pet_name='Whiskers'))} Whiskers task(s)")
feeding.complete()   # <-- no scheduler call needed
whiskers_tasks = scheduler.filter_tasks(pet_name="Whiskers")
print(f"  After:  {len(whiskers_tasks)} Whiskers task(s)")
for t in whiskers_tasks:
    status = "[done]" if t.is_completed else "[todo]"
    print(f"  {status} {t.due_date:%Y-%m-%d %H:%M}  {t.title}")

# PATH B: call scheduler.complete_task() — same result, explicit API
section("B. scheduler.complete_task() — weekly Grooming (Buddy)")
grooming = next(t for t in buddy.get_tasks() if t.task_id == "t6")
print(f"  Before: {len(scheduler.filter_tasks(pet_name='Buddy'))} Buddy task(s)")
scheduler.complete_task(grooming)
buddy_tasks = scheduler.filter_tasks(pet_name="Buddy")
print(f"  After:  {len(buddy_tasks)} Buddy task(s)")
for t in buddy_tasks:
    status = "[done]" if t.is_completed else "[todo]"
    print(f"  {status} {t.due_date:%Y-%m-%d %H:%M}  {t.title}")

# PATH C: ONCE task — no new occurrence created
section("C. ONCE task complete — no follow-up scheduled (Vet Check-up)")
vet = next(t for t in whiskers.get_tasks() if t.task_id == "t4")
count_before = len(scheduler.filter_tasks(pet_name="Whiskers"))
vet.complete()
count_after = len(scheduler.filter_tasks(pet_name="Whiskers"))
print(f"  Task count before: {count_before}  after: {count_after}  (no new task — correct)")

# Mark Morning Walk done so we can demo the completed filter below
scheduler.complete_task(
    next(t for t in buddy.get_tasks() if t.task_id == "t1")
)

# ── 1. sort_by_time — all tasks, insertion vs sorted order ──────────────────
section("1. All tasks — insertion order (unsorted)")
for task, _ in scheduler._registry.items():
    t, p = scheduler._registry[task]
    print(f"  {t.due_date:%H:%M}  [{t.priority:<6}]  {t.title} ({p.name})")

section("2. sort_by_time() — chronological, priority breaks ties")
for t in scheduler.sort_by_time():
    done = " [done]" if t.is_completed else ""
    print(f"  {t.due_date:%H:%M}  [{t.priority:<6}]  {t.title}{done}")

section("3. sort_by_time(reverse=True) — latest first")
for t in scheduler.sort_by_time(reverse=True):
    print(f"  {t.due_date:%H:%M}  [{t.priority:<6}]  {t.title}")


# ── 2. filter_tasks ─────────────────────────────────────────────────────────
section("4. filter_tasks(pet_name='Buddy') — all Buddy tasks")
for t in scheduler.filter_tasks(pet_name="Buddy"):
    status = "done" if t.is_completed else "todo"
    print(f"  {t.due_date:%H:%M}  [{t.priority:<6}]  {t.title}  ({status})")

section("5. filter_tasks(pet_name='Whiskers') — all Whiskers tasks")
for t in scheduler.filter_tasks(pet_name="Whiskers"):
    print(f"  {t.due_date:%H:%M}  [{t.priority:<6}]  {t.title}")

section("6. filter_tasks(completed=False) — incomplete tasks across all pets")
for t in scheduler.filter_tasks(completed=False):
    print(f"  {t.due_date:%H:%M}  [{t.priority:<6}]  {t.title}")

section("7. filter_tasks(completed=True) — completed tasks only")
for t in scheduler.filter_tasks(completed=True):
    print(f"  {t.due_date:%H:%M}  [{t.priority:<6}]  {t.title}")

section("8. filter_tasks(pet_name='buddy', completed=False) — case-insensitive, Buddy incomplete")
for t in scheduler.filter_tasks(pet_name="buddy", completed=False):
    print(f"  {t.due_date:%H:%M}  [{t.priority:<6}]  {t.title}")


# ── 3. Conflict detection ────────────────────────────────────────────────────
section("9. Conflict detection + slot suggestion")
probe = Task("t99", "Agility Training", "Obstacle course",
             due_date=now.replace(hour=9, minute=10),
             frequency=Frequency.ONCE, priority="medium", duration_minutes=30)
if scheduler.check_conflict(probe, buddy) is not None:
    slot = scheduler.suggest_next_slot(probe, buddy)
    print(f"  '{probe.title}' at 09:10 conflicts with Buddy's 09:00 Grooming.")
    print(f"  Next free slot: {slot:%H:%M}")


# ── 4. Recurring preview ─────────────────────────────────────────────────────
section("10. preview_recurring — Whiskers' Feeding (next 5 days)")
feeding = next(t for t in whiskers.get_tasks() if t.task_id == "t3")
for dt in preview_recurring(feeding, n=5):
    print(f"  {dt:%A %Y-%m-%d %H:%M}")
