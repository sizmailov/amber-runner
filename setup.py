from setuptools import setup

setup(
    name='amber-runner',
    maintainer="Sergei Izmailov",
    maintainer_email="sergei.a.izmailov@gmail.com",
    description="Batch execution for Amber MD",
    url="https://github.com/sizmailov/amber-runner",
    version="0.0.8",
    long_description=open("README.rst").read(),
    license="BSD",
    install_requires=[
        'remote-runner~=0.2',
        'f90nml'
    ],
    tests_require=[
        'pytest'
    ],
    packages=[
        'amber_runner'
    ]
)
