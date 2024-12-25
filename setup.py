from setuptools import find_packages, setup

setup(
    name="gphotos_mobile_client",
    version="0.2.0",
    description="Reverse engineered Google Photos mobile API client",
    author="xob0t",
    url="https://github.com/xob0t/gphotos_mobile_client",
    packages=find_packages(),
    install_requires=[
        "bbpb",
        "rich",
        "requests",
    ],
    entry_points={"console_scripts": ["gp-upload = gphotos_mobile_client.cli:main"]},
)
