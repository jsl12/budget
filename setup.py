from setuptools import setup, find_packages

setup(
    name='Budget',
    version='0.1',
    description='Budgeting system with plotting based on nested dictionaries of regex expressions',
    author='John Lancaster',
    author_email='lancaster.js@gmail.com',
    install_requires=[
        'matplotlib',
        'pandas',
        'pyyaml',
        'jupyter',
        'qgrid',
        'pyperclip',
    ],
    packages=find_packages()
)