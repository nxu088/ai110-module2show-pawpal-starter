from datetime import datetime, timedelta
from pawpal_system import Frequency, Pet, Scheduler, Task


def make_task(task_id: str = "t1", hours_from_now: float = 1.0) -> Task:
    return Task(
        task_id=task_id,
        title="Test Task",
        description="A test task",
        due_date=datetime.now() + timedelta(hours=hours_from_now),
        frequency=Frequency.ONCE,
    )


def make_pet(pet_id: str = "p1") -> Pet:
    return Pet(pet_id=pet_id, name="Buddy", species="Dog", breed="Labrador", age=3)


# --- Task Completion ---

def test_task_starts_incomplete():
    task = make_task()
    assert task.is_completed is False


def test_complete_marks_task_done():
    task = make_task()
    task.complete()
    assert task.is_completed is True


def test_complete_is_idempotent():
    task = make_task()
    task.complete()
    task.complete()
    assert task.is_completed is True


# --- Task Addition ---

def test_pet_starts_with_no_tasks():
    pet = make_pet()
    assert len(pet.get_tasks()) == 0


def test_add_task_increases_count():
    pet = make_pet()
    pet.add_task(make_task("t1"))
    assert len(pet.get_tasks()) == 1


def test_add_multiple_tasks_increases_count():
    pet = make_pet()
    pet.add_task(make_task("t1"))
    pet.add_task(make_task("t2"))
    assert len(pet.get_tasks()) == 2


def test_added_task_is_retrievable():
    pet = make_pet()
    task = make_task("t1")
    pet.add_task(task)
    assert task in pet.get_tasks()


# --- Sorting Correctness ---

def test_sort_by_time_chronological_order():
    """Tasks added out of order must come back sorted earliest-first."""
    pet = make_pet()
    scheduler = Scheduler()
    now = datetime.now().replace(second=0, microsecond=0)

    t_late  = Task("t_late",  "Late Task",   "", now.replace(hour=14, minute=0), Frequency.ONCE)
    t_early = Task("t_early", "Early Task",  "", now.replace(hour=7,  minute=0), Frequency.ONCE)
    t_mid   = Task("t_mid",   "Middle Task", "", now.replace(hour=10, minute=0), Frequency.ONCE)

    # Register intentionally out of order
    for task in (t_late, t_early, t_mid):
        scheduler.schedule_task(task, pet)

    sorted_tasks = scheduler.sort_by_time()
    due_times = [t.due_date for t in sorted_tasks]
    assert due_times == sorted(due_times), "Tasks are not in chronological order"


def test_sort_by_time_priority_breaks_tie():
    """When two tasks share the same due_date, high priority must come first."""
    pet = make_pet()
    scheduler = Scheduler()
    now = datetime.now().replace(second=0, microsecond=0)
    same_time = now.replace(hour=9, minute=0)

    t_low  = Task("tL", "Low",  "", same_time, Frequency.ONCE, priority="low")
    t_high = Task("tH", "High", "", same_time, Frequency.ONCE, priority="high")

    scheduler.schedule_task(t_low, pet)
    scheduler.schedule_task(t_high, pet)

    result = scheduler.sort_by_time()
    assert result[0].priority == "high", "High-priority task should sort before low-priority at the same time"


def test_sort_by_time_reverse():
    """reverse=True must return latest task first."""
    pet = make_pet()
    scheduler = Scheduler()
    now = datetime.now().replace(second=0, microsecond=0)

    t1 = Task("t1", "Early", "", now.replace(hour=7,  minute=0), Frequency.ONCE)
    t2 = Task("t2", "Late",  "", now.replace(hour=15, minute=0), Frequency.ONCE)

    scheduler.schedule_task(t1, pet)
    scheduler.schedule_task(t2, pet)

    result = scheduler.sort_by_time(reverse=True)
    assert result[0].task_id == "t2", "Latest task should be first when reverse=True"


# --- Recurrence Logic ---

def test_daily_task_creates_next_occurrence_on_complete():
    """Completing a DAILY task must add exactly one new task to the registry."""
    pet = make_pet()
    scheduler = Scheduler()
    now = datetime.now().replace(second=0, microsecond=0)

    task = Task("tr1", "Daily Feed", "", now.replace(hour=8, minute=0), Frequency.DAILY)
    scheduler.schedule_task(task, pet)

    count_before = len(scheduler._registry)
    task.complete()
    count_after = len(scheduler._registry)

    assert count_after == count_before + 1, "Completing a daily task should add one new occurrence"


def test_daily_next_occurrence_due_date_is_tomorrow():
    """The rescheduled task's due_date must be exactly one day after the original."""
    pet = make_pet()
    scheduler = Scheduler()
    now = datetime.now().replace(second=0, microsecond=0)
    original_due = now.replace(hour=8, minute=0)

    task = Task("tr2", "Daily Walk", "", original_due, Frequency.DAILY)
    scheduler.schedule_task(task, pet)
    task.complete()

    next_task = scheduler._registry["tr2_r"][0]
    assert next_task.due_date == original_due + timedelta(days=1), \
        "Next occurrence due_date should be original + 1 day"


def test_once_task_does_not_reschedule():
    """Completing a ONCE task must not add any new task to the registry."""
    pet = make_pet()
    scheduler = Scheduler()
    now = datetime.now().replace(second=0, microsecond=0)

    task = Task("to1", "One-time Vet", "", now.replace(hour=10, minute=0), Frequency.ONCE)
    scheduler.schedule_task(task, pet)

    count_before = len(scheduler._registry)
    task.complete()
    count_after = len(scheduler._registry)

    assert count_after == count_before, "ONCE task should not create a follow-up occurrence"


def test_weekly_next_occurrence_due_date_is_seven_days_later():
    """The rescheduled task's due_date must be exactly 7 days after the original."""
    pet = make_pet()
    scheduler = Scheduler()
    now = datetime.now().replace(second=0, microsecond=0)
    original_due = now.replace(hour=10, minute=0)

    task = Task("tr3", "Weekly Grooming", "", original_due, Frequency.WEEKLY)
    scheduler.schedule_task(task, pet)
    task.complete()

    next_task = scheduler._registry["tr3_r"][0]
    assert next_task.due_date == original_due + timedelta(weeks=1), \
        "Next occurrence due_date should be original + 7 days"


# --- Conflict Detection ---

def test_check_conflict_detects_same_pet_overlap():
    """Two overlapping tasks for the same pet must return a warning string."""
    pet = make_pet()
    scheduler = Scheduler()
    now = datetime.now().replace(second=0, microsecond=0)

    existing = Task("tc1", "Morning Walk", "", now.replace(hour=7, minute=0),
                    Frequency.ONCE, duration_minutes=30)
    scheduler.schedule_task(existing, pet)

    # Starts at 07:15 — inside the 07:00-07:30 window
    overlap = Task("tc2", "Agility", "", now.replace(hour=7, minute=15),
                   Frequency.ONCE, duration_minutes=30)

    warning = scheduler.check_conflict(overlap, pet)
    assert warning is not None, "Expected a conflict warning for overlapping same-pet tasks"
    assert "WARNING" in warning


def test_check_conflict_no_warning_when_clear():
    """A task starting after the prior one ends must return None (no conflict)."""
    pet = make_pet()
    scheduler = Scheduler()
    now = datetime.now().replace(second=0, microsecond=0)

    existing = Task("tc3", "Morning Walk", "", now.replace(hour=7, minute=0),
                    Frequency.ONCE, duration_minutes=30)
    scheduler.schedule_task(existing, pet)

    # Starts at 07:30 — exactly when the walk ends, so no overlap
    clear = Task("tc4", "Feeding", "", now.replace(hour=7, minute=30),
                 Frequency.ONCE, duration_minutes=15)

    warning = scheduler.check_conflict(clear, pet)
    assert warning is None, "Expected no conflict when task starts as the prior one ends"


def test_check_conflict_detects_cross_pet_overlap():
    """An owner cannot handle two pets at the same time — cross-pet overlap must warn."""
    buddy    = Pet("p1", "Buddy",    "Dog", "Labrador", 3)
    whiskers = Pet("p2", "Whiskers", "Cat", "Siamese",  5)
    scheduler = Scheduler()
    now = datetime.now().replace(second=0, microsecond=0)

    existing = Task("tc5", "Feeding", "", now.replace(hour=8, minute=0),
                    Frequency.ONCE, duration_minutes=15)
    scheduler.schedule_task(existing, whiskers)

    # Buddy task overlaps Whiskers' feeding window
    overlap = Task("tc6", "Buddy Breakfast", "", now.replace(hour=8, minute=5),
                   Frequency.ONCE, duration_minutes=10)

    warning = scheduler.check_conflict(overlap, buddy)
    assert warning is not None, "Expected a cross-pet conflict warning"
    assert "Whiskers" in warning, "Warning should name the conflicting pet"


def test_get_all_conflicts_finds_all_pairs():
    """get_all_conflicts must return one entry per overlapping pair."""
    pet = make_pet()
    scheduler = Scheduler()
    now = datetime.now().replace(second=0, microsecond=0)

    # Three tasks, all overlapping each other at 09:00
    for i, title in enumerate(("A", "B", "C")):
        scheduler.schedule_task(
            Task(f"tg{i}", title, "", now.replace(hour=9, minute=0),
                 Frequency.ONCE, duration_minutes=30),
            pet,
        )

    conflicts = scheduler.get_all_conflicts()
    # Three pairs: (A,B), (A,C), (B,C)
    assert len(conflicts) == 3, f"Expected 3 conflict pairs, got {len(conflicts)}"


def test_get_all_conflicts_empty_when_no_overlap():
    """get_all_conflicts must return an empty list when no tasks overlap."""
    pet = make_pet()
    scheduler = Scheduler()
    now = datetime.now().replace(second=0, microsecond=0)

    # Tasks spaced 1 hour apart, each 15 minutes long — no overlap
    for i in range(3):
        scheduler.schedule_task(
            Task(f"ts{i}", f"Task {i}", "", now.replace(hour=7 + i, minute=0),
                 Frequency.ONCE, duration_minutes=15),
            pet,
        )

    assert scheduler.get_all_conflicts() == []
