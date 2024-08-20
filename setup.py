from setuptools import setup, find_packages

setup(
    name='streamlit_app.py',
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
