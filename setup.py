from setuptools import setup, find_packages

setup(
    name='Budget',
    version='0.1',
    description='Budgeting system with plotting based on nested dictionaries of regex expressions',
    author='John Lancaster',
    author_email='lancaster.js@gmail.com',
    install_requires=[
        'pandas',
        'matplotlib',
        'pyyaml',
        'dash',
        'dash-bootstrap-components',
        'Flask-Session',
        'python-memcached'
    ],
    packages=find_packages()
)