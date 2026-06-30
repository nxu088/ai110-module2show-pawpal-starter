from datetime import datetime, timedelta
from pawpal_system import Frequency, Owner, Pet, Scheduler, Task

# --- Setup ---
owner = Owner(
    owner_id="o1",
    name="Alex Johnson",
    email="alex@example.com",
    phone="555-0100",
)

buddy = Pet(pet_id="p1", name="Buddy", species="Dog", breed="Labrador", age=3)
whiskers = Pet(pet_id="p2", name="Whiskers", species="Cat", breed="Siamese", age=5)

owner.add_pet(buddy)
owner.add_pet(whiskers)

scheduler = Scheduler()

now = datetime.now()

# Buddy's tasks
scheduler.schedule_task(
    Task("t1", "Morning Walk", "30-min walk around the park",
         due_date=now.replace(hour=7, minute=0, second=0, microsecond=0),
         frequency=Frequency.DAILY),
    buddy,
)
scheduler.schedule_task(
    Task("t2", "Flea Treatment", "Apply monthly flea drops",
         due_date=now.replace(hour=10, minute=30, second=0, microsecond=0),
         frequency=Frequency.MONTHLY),
    buddy,
)

# Whiskers' tasks
scheduler.schedule_task(
    Task("t3", "Feeding", "Wet food — half a can",
         due_date=now.replace(hour=8, minute=0, second=0, microsecond=0),
         frequency=Frequency.DAILY),
    whiskers,
)
scheduler.schedule_task(
    Task("t4", "Vet Check-up", "Annual wellness exam",
         due_date=now + timedelta(hours=3),
         frequency=Frequency.ONCE),
    whiskers,
)

# --- Print Today's Schedule ---
def print_schedule(owner: Owner, scheduler: Scheduler) -> None:
    divider = "-" * 40
    print(divider)
    print(f"  PawPal — Today's Schedule for {owner.name}")
    print(divider)

    upcoming = owner.view_schedule(scheduler)
    overdue  = [t for t in scheduler.get_overdue_tasks()
                if any(t in p.get_tasks() for p in owner.get_pets())]

    if overdue:
        print("\n  OVERDUE")
        for task in overdue:
            print(f"  [!] {task.due_date:%H:%M}  {task.title} — {task.description}")

    if upcoming:
        print("\n  UPCOMING")
        for task in upcoming:
            pet_name = next(
                p.name for p in owner.get_pets() if task in p.get_tasks()
            )
            print(f"  [ ] {task.due_date:%H:%M}  {task.title} ({pet_name}) — {task.description}")
    else:
        print("\n  No upcoming tasks.")

    print(divider)

print_schedule(owner, scheduler)
