from setuptools import setup, find_packages

setup(
    name="dlt-source-affinity",
    version="0.1.0",
    author="Joscha Feth",
    author_email="joscha@planet-a.com",
    packages=find_packages(exclude=["tests"]),
    description="A source for the Affinity CRM",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    install_requires=[
        "dlt",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
