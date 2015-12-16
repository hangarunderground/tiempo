from tiempo.work import Trabajo

unplanned_task = Trabajo(priority=1)
minutely_task = Trabajo(priority=1, periodic=True)
hourly_task = Trabajo(priority=1, periodic=True, minute=30)
daily_task = Trabajo(priority=1, periodic=True, hour=1)
monthly_task = Trabajo(priority=1, periodic=True, day=4, minute=17, hour=14)
