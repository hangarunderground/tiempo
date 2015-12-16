Tiempo is careful to refrain from relying on program state for scheduling and queueing tasks.  As such, it's possible to stop, reconfigure, and restart Tiempo processes without service interruption if done during a period where no Job run time will be missed during the downtime.
 
 Tiempo does keep a few crucial bits of information in program state:
 
 ## TIEMPO_REGISTRY

tiempo.TIEMPO_REGISTRY is a singleton dictionary that tracks Trabajo objects, both planned and unplanned.