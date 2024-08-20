from setuptools import setup, find_packages

setup(
    name='Your App Name',
    version='1.0',
    packages=find_packages(),
    install_requires=[
        'streamlit',
        'requests',
        'beautifulsoup4',
        'pandas',
        'matplotlib',
        'openai',
        'reportlab',
    ],
)