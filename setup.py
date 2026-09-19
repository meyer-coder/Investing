from setuptools import setup

setup(
    name="harvest",
    version="0.1.0",
    description="Pull years of TradingView candles and keep them on disk.",
    packages=["harvester"],
    python_requires=">=3.9",
    install_requires=["numpy>=1.24"],
    entry_points={"console_scripts": ["harvest = harvester.cli:main"]},
)
