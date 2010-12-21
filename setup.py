from setuptools import setup

setup(
    name='todo',
    version='0.8a.dev',
    description=' A task manager for Mozilla\'s localization dashboard.',
    author='Stas Malolepszy',
    author_email='stas@mozilla.com',
    url='http://github.com/stasm/todo',
    license='MPL 1.1/GPL 2.0/LGPL 2.1',
    packages=['todo'],
    install_requires=['Django >=1.1.2'],
)
