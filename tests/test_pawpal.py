from datetime import datetime, timedelta
from pawpal_system import Frequency, Pet, Task


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
