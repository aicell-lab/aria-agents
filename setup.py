import setuptools

# Read dependencies from requirements.txt
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setuptools.setup(
    install_requires=requirements,
)
