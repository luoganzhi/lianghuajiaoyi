from setuptools import setup, find_packages

setup(
    name="lianghuajiaoyi",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pandas",
        "numpy",
        "matplotlib",
        "jinja2",  # 用于HTML报告生成
    ],
    python_requires=">=3.7",
    author="lgzyy",
    description="量化交易系统",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
) 