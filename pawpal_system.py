from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Frequency(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    due_date: datetime
    frequency: Frequency = Frequency.ONCE
    is_completed: bool = False

    def complete(self) -> None:
        """Mark this task as completed."""
        self.is_completed = True

    def reschedule(self, new_date: datetime) -> None:
        """Move the task's due date to new_date."""
        self.due_date = new_date

    def is_overdue(self) -> bool:
        """Return True if the task is incomplete and past its due date."""
        return not self.is_completed and datetime.now() > self.due_date


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
        """Register a task with its associated pet."""
        pet.add_task(task)
        self._registry[task.task_id] = (task, pet)

    def cancel_task(self, task: Task) -> None:
        """Remove a task from its pet and from the registry."""
        entry = self._registry.pop(task.task_id, None)
        if entry:
            _, pet = entry
            pet.remove_task(task)

    def get_upcoming_tasks(self) -> list[Task]:
        """All incomplete, not-yet-overdue tasks sorted by due date."""
        upcoming = [
            task for task, _ in self._registry.values()
            if not task.is_completed and not task.is_overdue()
        ]
        return sorted(upcoming, key=lambda t: t.due_date)

    def get_tasks_for_pet(self, pet: Pet) -> list[Task]:
        """All tasks registered for a specific pet, sorted by due date."""
        tasks = [
            task for task, owner_pet in self._registry.values()
            if owner_pet is pet
        ]
        return sorted(tasks, key=lambda t: t.due_date)

    def get_overdue_tasks(self) -> list[Task]:
        """All incomplete tasks whose due date has passed, sorted by due date."""
        overdue = [
            task for task, _ in self._registry.values()
            if task.is_overdue()
        ]
        return sorted(overdue, key=lambda t: t.due_date)
