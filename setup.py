from setuptools import setup
setup(
    name="chaintrap-maptool",
    entry_points={
        "console_scripts": [
            "maptool = maptool.map:main",
        ]
    },
    packages=["maptool", "vrf", "service"]
)
