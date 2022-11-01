import setuptools
import pathlib

# read README.md
root = pathlib.Path(__file__).parent.resolve()
long_description = (root / "README.md").read_text(encoding="utf-8")
version = (root / "inigo_py" / "VERSION").read_text(encoding="utf-8").strip()

setuptools.setup(
    name='inigo_py',
    version=version,
    author='Nikolai Kaploniuk',
    author_email='nkaploniuk@inigo.io',
    description='Inigo Middleware',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/kolia-kaploniuk/inigo-py',
    project_urls={
        "Bug Tracker": "https://github.com/kolia-kaploniuk/inigo-py/issues",
        "Documentation": "https://docs.inigo.io",
        "Support": "https://slack.inigo.io",
    },
    license='MIT',
    packages=['inigo_py'],
    install_requires=['pyjwt', 'django'],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Framework :: Django',
        'License :: OSI Approved :: MIT License',
        'Typing :: Typed',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Programming Language :: Python :: 3',
    ],
    keywords="api graphql inigo django graphene",
    package_data={
        'inigo_py': [
            'lib/*',
            'VERSION'
        ]
    },
)
