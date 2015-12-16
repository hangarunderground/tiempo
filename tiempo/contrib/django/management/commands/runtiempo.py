from django.core.management.base import BaseCommand
import sys
import time

from twisted.internet import threads, task, reactor

from tiempo.execution import ThreadManager

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('groups', type=str)

    def handle(self, *args, **options):

        groups = options.get('groups', '1')

        thread_group_list = groups.split(',')

        tm = ThreadManager(1, thread_group_list)
        tm.start()

        reactor.run()

