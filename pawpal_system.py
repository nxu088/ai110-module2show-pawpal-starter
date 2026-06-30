from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class Frequency(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


_FREQUENCY_DELTA: dict[Frequency, timedelta] = {
    Frequency.DAILY:   timedelta(days=1),
    Frequency.WEEKLY:  timedelta(weeks=1),
    Frequency.MONTHLY: timedelta(days=30),
}

_PRIORITY_ORDER: dict[str, int] = {"high": 0, "medium": 1, "low": 2}


def _sort_key(task: Task) -> tuple:
    """Primary sort key for all task lists: chronological, then high-priority first."""
    return (task.due_date, _PRIORITY_ORDER.get(task.priority, 99))


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    due_date: datetime
    frequency: Frequency = Frequency.ONCE
    is_completed: bool = False
    priority: str = "medium"        # "low" | "medium" | "high"
    duration_minutes: int = 30
    # Set by Scheduler.schedule_task(); fires auto-reschedule on completion.
    _on_complete: object = field(default=None, repr=False, compare=False)

    def complete(self) -> None:
        """Mark this task completed and trigger auto-reschedule if recurring."""
        if self.is_completed:
            return
        self.is_completed = True
        if self._on_complete is not None:
            self._on_complete(self)

    def reschedule(self, new_date: datetime) -> None:
        """Move the task's due date to new_date."""
        self.due_date = new_date

    def is_overdue(self) -> bool:
        """Return True if the task is incomplete and past its due date."""
        return not self.is_completed and datetime.now() > self.due_date


def preview_recurring(task: Task, n: int = 5) -> list[datetime]:
    """Return the next n due datetimes for a recurring task (includes the current one).

    Algorithm:
        Looks up the timedelta for the task's frequency in _FREQUENCY_DELTA, then
        uses list comprehension with scalar multiplication (delta * i) to shift the
        base due_date forward by 0, 1, 2 … n-1 intervals.  No calendar library is
        needed because timedelta arithmetic handles month/year boundaries automatically.
        ONCE tasks have no delta entry and return a single-element list.

    Args:
        task: The recurring task whose schedule to preview.
        n:    Number of occurrences to generate (default 5).

    Returns:
        List of datetime objects, earliest first.
    """
    delta = _FREQUENCY_DELTA.get(task.frequency)
    if not delta:
        return [task.due_date]
    return [task.due_date + delta * i for i in range(n)]


@dataclass
class Pet:
    pet_id: str
    name: str
    species: str
    breed: str
    age: int
    _tasks: list[Task] = field(default_factory=list, repr=False)

    def add_task(self, task: Task) -> None:
        """Append a task to this pet's task list."""
        self._tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task from this pet's task list."""
        self._tasks.remove(task)

    def get_tasks(self) -> list[Task]:
        """Return a copy of this pet's task list."""
        return list(self._tasks)


class Owner:
    def __init__(self, owner_id: str, name: str, email: str, phone: str) -> None:
        self.owner_id = owner_id
        self.name = name
        self.email = email
        self.phone = phone
        self._pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's roster."""
        self._pets.append(pet)

    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from this owner's roster."""
        self._pets.remove(pet)

    def get_pets(self) -> list[Pet]:
        """Return a copy of this owner's pet list."""
        return list(self._pets)

    def get_all_tasks(self) -> list[Task]:
        """Returns every task across all owned pets, sorted by due date."""
        all_tasks = [task for pet in self._pets for task in pet.get_tasks()]
        return sorted(all_tasks, key=lambda t: t.due_date)

    def view_schedule(self, scheduler: Scheduler) -> list[Task]:
        """Returns upcoming (non-overdue, incomplete) tasks for all owned pets."""
        all_pet_tasks = [task for pet in self._pets for task in pet.get_tasks()]
        return [t for t in scheduler.get_upcoming_tasks() if t in all_pet_tasks]


class Scheduler:
    def __init__(self) -> None:
        # maps task_id -> (Task, Pet) so the brain knows which pet each task belongs to
        self._registry: dict[str, tuple[Task, Pet]] = {}

    def schedule_task(self, task: Task, pet: Pet) -> None:
        """Register a task with its associated pet and wire the auto-reschedule callback."""
        pet.add_task(task)
        self._registry[task.task_id] = (task, pet)
        task._on_complete = self._auto_reschedule

    def _auto_reschedule(self, task: Task) -> None:
        """Callback invoked by Task.complete() — enqueues the next occurrence if recurring.

        Algorithm:
            Uses the observer/callback pattern: schedule_task() stores a reference to
            this method on task._on_complete; Task.complete() calls it with itself as
            the argument.  This keeps Task decoupled from Scheduler — Task never imports
            or references the Scheduler class.

            Steps:
            1. Look up the completed task in _registry to find its owning pet.
            2. Look up the frequency-to-timedelta mapping.  If frequency is ONCE (no
               entry in _FREQUENCY_DELTA), return early — no follow-up task is created.
            3. Build a new Task with the same metadata but due_date shifted forward by
               one interval (task.due_date + delta).
            4. Call schedule_task() on the new task, which wires the callback again so
               the chain continues on each subsequent completion.

        Args:
            task: The just-completed Task that may need a follow-up occurrence.
        """
        entry = self._registry.get(task.task_id)
        if entry is None:
            return
        _, pet = entry
        delta = _FREQUENCY_DELTA.get(task.frequency)
        if delta is None:
            return
        next_task = Task(
            task_id=f"{task.task_id}_r",
            title=task.title,
            description=task.description,
            due_date=task.due_date + delta,
            frequency=task.frequency,
            priority=task.priority,
            duration_minutes=task.duration_minutes,
        )
        self.schedule_task(next_task, pet)

    def cancel_task(self, task: Task) -> None:
        """Remove a task from its pet and from the registry."""
        entry = self._registry.pop(task.task_id, None)
        if entry:
            _, pet = entry
            pet.remove_task(task)

    # --- Unified filter ---
    def get_tasks(
        self,
        pet: "Pet | str | None" = None,
        completed: bool | None = None,
        overdue_only: bool = False,
    ) -> list[Task]:
        """Return tasks filtered by pet, completion status, and/or overdue state.

        Args:
            pet:          A Pet object (identity match), a name string (case-insensitive),
                          or None to include all pets.
            completed:    True: completed only, False: incomplete only, None: both.
            overdue_only: If True, only include tasks past their due date.

        Returns:
            Filtered list sorted by (due_date, priority).
        """
        results = []
        for task, owner_pet in self._registry.values():
            if pet is not None:
                if isinstance(pet, Pet):
                    if owner_pet is not pet:
                        continue
                else:
                    if owner_pet.name.lower() != pet.lower():
                        continue
            if completed is not None and task.is_completed != completed:
                continue
            if overdue_only and not task.is_overdue():
                continue
            results.append(task)
        return sorted(results, key=_sort_key)

    def filter_tasks(
        self,
        pet_name: str | None = None,
        completed: bool | None = None,
    ) -> list[Task]:
        """Thin wrapper over get_tasks() for string-name pet filtering.

        Accepts a pet name string (case-insensitive) for compatibility with UI
        widgets such as Streamlit's st.selectbox, which returns strings not Pet objects.

        Args:
            pet_name:  Case-insensitive name string; None returns tasks for all pets.
            completed: True → completed only, False → incomplete only, None → both.
        """
        return self.get_tasks(pet=pet_name, completed=completed)

    # --- Sorting ---
    def sort_by_time(
        self,
        tasks: list[Task] | None = None,
        reverse: bool = False,
    ) -> list[Task]:
        """Return tasks sorted by due_date, then by priority within the same minute.

        Algorithm:
            Uses Python's built-in sorted() with a two-element tuple key:
                key = (task.due_date, _PRIORITY_ORDER[task.priority])
            sorted() compares tuples lexicographically — due_date is the primary sort
            key; the integer priority rank (0=high, 1=medium, 2=low) breaks ties so
            high-priority tasks always surface first when they share a start time.
            Tasks with unknown priority strings fall back to rank 99 (sorts last).

        Args:
            tasks:   Explicit list to sort.  If None, sorts every registered task.
            reverse: True for latest-first (descending) order.

        Returns:
            A new sorted list; the original list/registry is not mutated.
        """
        source = tasks if tasks is not None else [t for t, _ in self._registry.values()]
        return sorted(source, key=_sort_key, reverse=reverse)

    # --- Convenience wrappers used by app.py ---
    def get_upcoming_tasks(self) -> list[Task]:
        """All incomplete, not-yet-overdue tasks sorted by due date + priority."""
        return [t for t in self.get_tasks(completed=False) if not t.is_overdue()]

    def get_overdue_tasks(self) -> list[Task]:
        """All incomplete overdue tasks sorted by due date + priority."""
        return self.get_tasks(completed=False, overdue_only=True)

    # --- Recurring task completion ---
    def complete_task(self, task: Task) -> None:
        """Mark task complete; auto-reschedule fires via the callback if recurring."""
        task.complete()

    # --- Conflict detection ---
    def check_conflict(self, new_task: Task, pet: Pet) -> str | None:
        """Return a warning string if new_task overlaps an existing task, else None.

        Algorithm:
            Extends has_conflict() in two ways:
            (a) Scope — checks ALL incomplete tasks in the registry, not just the
                target pet's.  An owner can only be in one place at a time, so a
                Buddy task at 08:00 conflicts with a Whiskers task at 08:05 too.
            (b) Return value — returns a human-readable string instead of a bool,
                so callers can display the warning without wrapping in try/except.
                Returns None (falsy) when no conflict is found, making ``if msg:``
                the natural usage pattern.

            The overlap formula is identical to has_conflict():
                new_start < ex_end  AND  new_end > ex_start
            The inverse guard ``new_start >= ex_end or new_end <= ex_start`` skips
            non-overlapping pairs early, so the expensive string-building only runs
            on the first conflict found.

            Scope label in the warning string:
                "same pet"              — owner_pet is the same object as pet
                "different pet (Name)"  — cross-pet conflict, shows the other pet's name

        Args:
            new_task: The candidate task to test before scheduling.
            pet:      The pet the new task would be assigned to.

        Returns:
            A warning string describing the overlap, or None if the slot is clear.
        """
        new_start = new_task.due_date
        new_end   = new_start + timedelta(minutes=new_task.duration_minutes)

        for existing, owner_pet in (
            (t, p) for t, p in self._registry.values() if not t.is_completed
        ):
            if existing.task_id == new_task.task_id:
                continue
            ex_start = existing.due_date
            ex_end   = ex_start + timedelta(minutes=existing.duration_minutes)
            if new_start >= ex_end or new_end <= ex_start:
                continue

            # Overlap found — build a descriptive message
            scope = "same pet" if owner_pet is pet else f"different pet ({owner_pet.name})"
            return (
                f"WARNING: '{new_task.title}' ({pet.name}, "
                f"{new_start:%H:%M}-{new_end:%H:%M}) overlaps "
                f"'{existing.title}' ({scope}, "
                f"{ex_start:%H:%M}-{ex_end:%H:%M})"
            )
        return None

    def get_all_conflicts(self) -> list[str]:
        """Scan every registered incomplete task pair and return all overlap warnings.

        Algorithm:
            O(n²) nested-loop over all incomplete tasks.  The inner loop starts at
            index i+1 (``entries[i + 1:]``) so each unordered pair (A, B) is visited
            exactly once — B vs A is never re-checked, avoiding duplicate warnings.

            For each pair the same half-open interval test is applied:
                a_start < b_end  AND  a_end > b_start  →  overlap
            The inverse guard ``a_start >= b_end or a_end <= b_start`` skips clean
            pairs with a single comparison, keeping the common (no-conflict) path fast.

            Scope label in each warning string:
                "same pet"       — both tasks belong to the same Pet object
                "PetA & PetB"    — cross-pet conflict, names both owners

            Practical use: call after bulk-adding tasks to surface all scheduling
            problems at once, rather than discovering them one at a time.

        Returns:
            List of warning strings, one per conflicting pair.  Empty list means
            the schedule is conflict-free.
        """
        warnings: list[str] = []
        entries = [
            (task, pet)
            for task, pet in self._registry.values()
            if not task.is_completed
        ]
        for i, (task_a, pet_a) in enumerate(entries):
            a_start = task_a.due_date
            a_end   = a_start + timedelta(minutes=task_a.duration_minutes)
            for task_b, pet_b in entries[i + 1:]:
                b_start = task_b.due_date
                b_end   = b_start + timedelta(minutes=task_b.duration_minutes)
                if a_start >= b_end or a_end <= b_start:
                    continue
                scope = "same pet" if pet_a is pet_b else f"{pet_a.name} & {pet_b.name}"
                warnings.append(
                    f"CONFLICT ({scope}): '{task_a.title}' "
                    f"{a_start:%H:%M}-{a_end:%H:%M} overlaps "
                    f"'{task_b.title}' {b_start:%H:%M}-{b_end:%H:%M}"
                )
        return warnings

    def suggest_next_slot(self, task: Task, pet: Pet, step_minutes: int = 15) -> datetime:
        """Return the earliest conflict-free start time at or after task.due_date.

        Algorithm:
            Linear scan (greedy step search) — starts at the requested due_date and
            advances by step_minutes until has_conflict() returns False:

                candidate = task.due_date
                while conflict:
                    candidate += timedelta(minutes=step_minutes)

            A temporary "probe" Task is mutated in place (probe.due_date = candidate)
            on each iteration to avoid allocating a new Task object per step.  The
            probe is never registered in the scheduler, so it does not affect the
            real schedule.

            Trade-off: step size controls resolution vs. speed.  Smaller steps find
            tighter fits but require more iterations.  15 minutes matches common
            calendar granularity and is rarely more than 4-5 iterations in practice.

        Args:
            task:         The task whose metadata (duration, priority) defines the
                          window to search for.
            pet:          The pet whose schedule must remain conflict-free.
            step_minutes: Increment between candidate slots (default 15).

        Returns:
            A datetime representing the earliest open start time.
        """
        step = timedelta(minutes=step_minutes)
        candidate = task.due_date
        probe = Task(
            task_id=f"__probe_{task.task_id}",
            title=task.title,
            description=task.description,
            due_date=candidate,
            frequency=task.frequency,
            priority=task.priority,
            duration_minutes=task.duration_minutes,
        )
        while self.check_conflict(probe, pet) is not None:
            candidate += step
            probe.due_date = candidate
        return candidate
