"""Sets up the parameters required by PyPI"""
from pathlib import Path
from setuptools import setup, find_packages

this_directory = Path(__file__).parent
long_description = (this_directory / 'README.md').read_text()

setup(
    name='mkdocs-categories-plugin',
    version='0.2.1',
    description=
    'An MkDocs plugin allowing for categorization of pages',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords='mkdocs python markdown category categories link wiki',
    url='https://github.com/eddyluten/mkdocs-categories-plugin',
    author='Eddy Luten',
    author_email='eddyluten@gmail.com',
    license='MIT',
    python_requires='>=3.0',
    install_requires=['mkdocs'],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages=find_packages(exclude=['*.tests']),
    entry_points={
        'mkdocs.plugins': ['categories = categories.plugin:CategoriesPlugin']
    })
