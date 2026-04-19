from setuptools import setup, find_packages

setup(
    name="stillhere-cli",
    version="1.0.0",
    description="CLI tool for Still Here self-hosted deployments",
    py_modules=["stillhere"],
    packages=find_packages(),
    install_requires=[
        "rich>=13.0",
        "click>=8.1",
        "psycopg2-binary>=2.9",
        "httpx>=0.27",
        "python-dotenv>=1.0",
    ],
    entry_points={
        "console_scripts": [
            "stillhere=stillhere:cli",
        ],
    },
    python_requires=">=3.10",
)
