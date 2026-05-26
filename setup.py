from pathlib import Path
from setuptools import setup, find_packages


def parse_requirements():
    requirements = []
    requirements_file = Path(__file__).with_name("requirements.txt")

    for line in requirements_file.read_text(encoding="utf-8").splitlines():
        requirement = line.split("#", 1)[0].strip()
        if requirement:
            requirements.append(requirement)

    return requirements

setup(
    name="lianghuajiaoyi",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=parse_requirements(),
    python_requires=">=3.8",
    author="lgzyy",
    description="量化交易系统",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
