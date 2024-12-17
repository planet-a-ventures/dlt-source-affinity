from setuptools import setup, find_packages

setup(
    name="dlt-source-affinity",
    version="0.1.0",
    author="Planet A GmbH",
    author_email="dev@planet-a.com",
    packages=find_packages(exclude=["tests"]),
    description="A DLT source for the Affinity CRM",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    install_requires=[
        "dlt>=1.4.1",
    ],
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
