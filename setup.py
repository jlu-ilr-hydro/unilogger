from setuptools import setup, find_packages

setup(
    name='unilogger',
    version='2022.9.5',
    packages=find_packages(),
    author='Philipp Kraft',
    author_email='philipp.kraft@umwelt.uni-giessen.de',
    description='A unified wrapper to log data from various sensor busses',
    install_requires=open('requirements.txt').readlines(),
    python_requires='>=3.8'
)