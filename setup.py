import os
from setuptools import setup, find_packages

src_dir = os.path.dirname(__file__)

install_requires = [
    "troposphere~=1.8.2",
    "awacs~=0.6.0",
    "stacker~=0.8.1",
]

tests_require = [
    "nose~=1.0",
    "mock~=2.0.0",
]


def read(filename):
    full_path = os.path.join(src_dir, filename)
    with open(full_path) as fd:
        return fd.read()


if __name__ == "__main__":
    setup(
        name="stacker_blueprints",
        version="0.7.2",
        author="Michael Barrett",
        author_email="loki77@gmail.com",
        license="New BSD license",
        url="https://github.com/remind101/stacker_blueprints",
        description="Default blueprints for stacker",
        long_description=read("README.rst"),
        packages=find_packages(),
        install_requires=install_requires,
        tests_require=tests_require,
        test_suite="nose.collector",
    )
