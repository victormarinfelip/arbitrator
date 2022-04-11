import io
import os

from setuptools import find_packages, setup

# Package meta-data.
NAME = "trading-arbitrator"
DESCRIPTION = "A powerful arbitrage calculator able to simulate AMM slippage"
EMAIL = "victor.marin.felip@gmail.com"
AUTHOR = "Victor Marin Felip"
REQUIRES_PYTHON = ">=3.8.0"
VERSION = "0.1.0"

# Which packages are required for this module to be executed?
REQUIRED = ["scipy"]

# The rest you shouldn't have to touch too much :)

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.md' is present in your MANIFEST.in file!
try:
    with io.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
        long_description = "\n" + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

# Load the package's __version__.py module as a dictionary.
about = {}
if not VERSION:
    project_slug = NAME.lower().replace("-", "_").replace(" ", "_")
    with open(os.path.join(here, project_slug, "__version__.py")) as f:
        exec(f.read(), about)
else:
    about["__version__"] = VERSION

setup(
    name=NAME,
    version=about["__version__"],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    packages=find_packages(exclude=("tests",)),
    include_package_data=True,
    package_data={"trading-arbitrator": ["*.pyi", "*.typed"]},
    install_requires=["scipy"],
    classifiers=[
        "Programming Language :: Python :: 3.8",
    ],
)
