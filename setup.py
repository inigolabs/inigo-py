from setuptools import find_packages, setup
import pathlib

# read README.md
root = pathlib.Path(__file__).parent.resolve()
long_description = (root / "README.md").read_text(encoding="utf-8")
version = (root / "inigo_py" / "VERSION").read_text(encoding="utf-8").strip()

install_requires = []

## werkzeug
install_flask_requires = [
    "flask>=2,<3",
    "werkzeug>=2.2.3,<3.0.0",
]

install_django_requires = [
    "django>=4,<5",
]

install_all_requires = (
        install_requires
        + install_flask_requires
        + install_django_requires
)


setup(
    name='inigo_py',
    version=version,
    author='Nikolai Kaploniuk',
    author_email='nkaploniuk@inigo.io',
    description='Inigo Middleware',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/inigolabs/inigo-py',
    project_urls={
        "Bug Tracker": "https://github.com/inigolabs/inigo-py/issues",
        "Documentation": "https://docs.inigo.io",
        "Support": "https://slack.inigo.io",
    },
    license='MIT',
    packages=find_packages(include=["inigo_py*"]),
    install_requires=[],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11'
    ],
    python_requires='>= 3.8',
    keywords="api graphql inigo graphene",
    package_data={
        'inigo_py': [
            'lib/*',
            'VERSION'
        ]
    },
    extras_require={
        "all": install_all_requires,
        "flask": install_flask_requires,
        "django": install_django_requires,
    },
)
