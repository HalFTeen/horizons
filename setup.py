"""Minimal setup.py for editable install without build backend."""
from setuptools import setup
from setuptools.command.develop import develop as develop_orig
import os


class develop(develop_orig):
    """Custom develop command that doesn't use build backend."""
    def run(self):
        os.environ["SETUPTOOLS_USE_BOOTSTRAP"] = "0"
        develop_orig.run(self)


if __name__ == "__main__":
    setup(
        name="horizons",
        version="0.1.0",
        packages=["horizons"],
        package_dir={"": "src"},
        cmdclass={"develop": develop},
    )
