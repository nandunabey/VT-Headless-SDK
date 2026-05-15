from setuptools import setup, find_packages

setup(
    name="vut-sdk",
    version="0.1.0a0",
    description=(
        "Unofficial community SDK for headless 6DoF spatial "
        "tracking with VIVE Ultimate Tracker. Not affiliated "
        "with HTC or Valve."
    ),
    author="Nandun Abeynayake",
    author_email="nandun.abey@gmail.com",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "websockets>=16.0",
    ],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.14",
        "Topic :: Software Development :: Libraries",
        "Topic :: Multimedia :: Graphics :: 3D Modeling",
    ],
)
