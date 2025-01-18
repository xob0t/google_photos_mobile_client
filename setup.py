from setuptools import find_packages, setup

setup(
    name="gpmc",
    version="0.4.7",
    python_requires=">=3.10",
    description="Reverse engineered Google Photos mobile API client",
    author="xob0t",
    url="https://github.com/xob0t/gphotos_mobile_client",
    packages=find_packages(),
    install_requires=[
        "bbpb",
        "rich",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "gp-upload = gpmc.cli:main",
            "gpmc = gpmc.cli:main",
        ]
    },
)
