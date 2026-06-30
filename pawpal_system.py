from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    due_date: datetime
    is_completed: bool = False

    def complete(self) -> None:
        raise NotImplementedError

    def reschedule(self, new_date: datetime) -> None:
        raise NotImplementedError

    def is_overdue(self) -> bool:
        raise NotImplementedError


@dataclass
class Pet:
    pet_id: str
    name: str
    species: str
    breed: str
    age: int
    _tasks: list[Task] = field(default_factory=list, repr=False)

    def add_task(self, task: Task) -> None:
        raise NotImplementedError

    def remove_task(self, task: Task) -> None:
        raise NotImplementedError

    def get_tasks(self) -> list[Task]:
        raise NotImplementedError


class Owner:
    def __init__(self, owner_id: str, name: str, email: str, phone: str) -> None:
        self.owner_id = owner_id
        self.name = name
        self.email = email
        self.phone = phone
        self._pets: list[Pet] = []

    def add_pet(self, pet: Pet) -> None:
        raise NotImplementedError

    def remove_pet(self, pet: Pet) -> None:
        raise NotImplementedError

    def get_pets(self) -> list[Pet]:
        raise NotImplementedError

    def view_schedule(self, scheduler: Scheduler) -> list[Task]:
        raise NotImplementedError


class Scheduler:
    def __init__(self) -> None:
        self._tasks: list[Task] = []

    def schedule_task(self, task: Task) -> None:
        raise NotImplementedError

    def cancel_task(self, task: Task) -> None:
        raise NotImplementedError

    def get_upcoming_tasks(self) -> list[Task]:
        raise NotImplementedError

    def get_tasks_for_pet(self, pet: Pet) -> list[Task]:
        raise NotImplementedError

    def get_overdue_tasks(self) -> list[Task]:
        raise NotImplementedError
