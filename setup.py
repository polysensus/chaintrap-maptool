from setuptools import setup
setup(
    name="toc",
    entry_points={
        "console_scripts": [
            "toc-maptool = maptool.map:main",
        ]
    },
    packages=["maptool", "vrf", "service"]
)
