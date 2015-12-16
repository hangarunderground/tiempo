from tiempo.work import Trabajo
import random
import time


def sleep_blocker(announcer):
    upper_bound = random.choice(range(60, 120))
    announcer.brief("Going to try to do %s things." % upper_bound)

    unlucky_number = random.choice(range(80, 160))

    announcer.set_progress_increments(upper_bound)  # TODO: Implement progress indicator.

    for n in range(0, upper_bound):
        announcer.report_progress(n)
        time.sleep(.1)
        if n == unlucky_number:
            raise RuntimeError("I am error.  Friend of bagu.  I hit unlucky number %s" % unlucky_number)

    announcer.brief("Everything went OK - %s things happened." % upper_bound)
    announcer.detail("Avoided unlucky number %s" % unlucky_number)
    announcer.detail(LOREM_IPSUM)

    return


@Trabajo(priority=1, periodic=True, announcer_name="announcer")
def dingo(announcer):
    sleep_blocker(announcer)


@Trabajo(periodic=True, force_interval=10, announcer_name="announcer")
def llama(announcer):
    sleep_blocker(announcer)

LOREM_IPSUM = """Lorizzle ipsum dolor hizzle amet, i'm in the shizzle adipiscing elit. Nullam sapien crackalackin, gangsta volutpizzle, suscipit quis, away vizzle, daahng dawg. Pellentesque gangster pizzle. Sed erizzle. Ass izzle we gonna chung dapibus i'm in the shizzle tempizzle uhuh ... yih!. Maurizzle gangsta nibh et turpis. Dizzle izzle tortor. Pellentesque away rhoncizzle pimpin'. In hac habitasse platea dizzle. Ass dapibizzle. Owned tellizzle sure, pretium gizzle, mattizzle sheezy, break yo neck, yall vitae, shizzle my nizzle crocodizzle. Boofron suscipizzle. Integer semper sheezy sizzle purus.

Fo shizzle mah nizzle fo rizzle, mah home g-dizzle shizzlin dizzle turpizzle izzle leo pizzle molestie. Stuff vestibulum boofron vizzle massa. Quisque dang ornare magna. Morbi commodo, shit nizzle bibendizzle egestizzle, yippiyo dolor vestibulum ligula, ac auctor justo its fo rizzle own yo' augue. Maecenas id elizzle shiznit amizzle eros adipiscing sagittizzle. Vivamizzle pizzle pimpin' hizzle lacus. Fo shizzle rhoncizzle own yo' leo. Shiz ipsizzle dolor sizzle you son of a bizzle, funky fresh adipiscing elizzle. Fo daahng dawg ligula, posuere sit uhuh ... yih!, dizzle sizzle, ma nizzle mattizzle, fizzle. Pimpin' tellivizzle faucibizzle diam. Fo shizzle my nizzle shut the shizzle up leo. Nunc sizzle own yo' dawg diam accumsizzle da bomb. Quisque mah nizzle metizzle laoreet nunc. Things nizzle, sheezy quizzle shizzle my nizzle crocodizzle i'm in the shizzle, lectus diam dawg felis, nec ullamcorper break yo neck, yall nisl the bizzle nisi. Vivamizzle tellivizzle mofo, aliquizzle gangsta gangster, ornare doggy, pulvinizzle pulvinizzle, my shizz.

Pot dawg ipsum primis sheezy faucibus orci shizznit et my shizz posuere check it out Curae; Sizzle vitae shiz quizzle neque ornare aliquam. Pimpin' euismod erizzle. Dang volutpizzle accumsizzle velizzle. Praesent dizzle gizzle, adipiscing get down get down, go to hizzle black, interdizzle bizzle, ante. Bizzle malesuada owned fo shizzle mah nizzle fo rizzle, mah home g-dizzle. Get down get down izzle check it out izzle augue porta dawg. Nizzle sed augue. Vivamus we gonna chung. Sheezy eu away quizzle lacizzle posuere for sure. Donec izzle break it down brizzle felizzle tincidunt mollis. Pot brizzle. Yo mamma scelerisque. Fo shizzle mah nizzle fo rizzle, mah home g-dizzle magna eros, brizzle get down get down, porttitizzle that's the shizzle, imperdizzle fo shizzle mah nizzle fo rizzle, mah home g-dizzle, orci. Integer we gonna chung sodales lectus. Etizzle sollicitudizzle ghetto sizzle. Gangster mi pimpin', convallizzle izzle, pellentesque ghetto, ultricizzle izzle, nibh. Fusce erizzle fo shizzle, ghetto fo shizzle, sollicitudizzle gangster, aliquizzle go to hizzle, lectizzle. Fusce break it down risus, mammasay mammasa mamma oo sa molestie, adipiscing ut, blandizzle sit break yo neck, yall, shizznit."""


