from redlock import RedLockFactory


lock_factory = RedLockFactory(connection_details=[
    {'host': 'localhost', 'port': 6379}
    ]
)

schedule_lock = lock_factory.create_lock("schedule_tasks_for_queueing")
