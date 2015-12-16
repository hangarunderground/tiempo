# tiempo
A Procrastination Framework for Python


## Dev Setup

```bash
virtualenv tiempo --no-site-packages --distributed
source tiempo/bin/activate
pip install -e <path to your tiempo repo>
```

Then to test this shit out just run:

```bash
./tiempo/scripts/metronome
```


#### To use with Django/Hendrix

*  in settings.py
  * `TIEMPO_THREAD_CONFIG = [('prioirty1'), ('priority1, 'downstairs', 'upstairs')]`
    * each entry in the list specifies which queues that thread should check for work 
    * the above example will have two both checking "priority1" and "downstairs" and "upstairs" on only one process
  * 'INSTALLED_APPS' += 'tiempo.contrib.django'
