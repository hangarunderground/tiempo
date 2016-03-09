from setuptools import setup, find_packages
import os
import tiempo


def file_name(rel_path):
    dir_path = os.path.dirname(__file__)
    return os.path.join(dir_path, rel_path)


def readlines(rel_path):
    with open(file_name(rel_path)) as f:
        ret = f.readlines()
    return ret


setup(
    author="Damon",
    name="tiempo",
    version=tiempo.__version__,
    packages=find_packages(exclude=["tests*", ]),
    url="https://github.com/hangarunderground/tiempo",
    description="Twisted task scheduling for django",
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    keywords=['twisted', 'tasks', 'redis', 'scheduling'],
    install_requires=readlines('requirements/requirements.txt'),
    extras_require={
        'dev': ['ipdb', 'django', 'hendrix', 'coverage'],
        'django': ['django', ]
    },
    include_package_data=True
)
