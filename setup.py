from setuptools import setup, find_packages

setup(
    name='unilogger',
    version='2022.9.13',
    packages=find_packages(),
    author='Philipp Kraft',
    author_email='philipp.kraft@umwelt.uni-giessen.de',
    description='A unified wrapper to log data from various sensor busses',
    install_requires=[
        'umodbus>1.0', 'aiohttp>3.7', 'BeautifulSoup4>4.9',
        'aioserial>=1.3.0', 'pyyaml>=6.0', 'lxml', 'pyserial>=3.5',
        'asteval>=0.9', 'pandas>=1.4', 'tables>=3.6', 'openpyxl'
    ],
    python_requires='>=3.8'
)