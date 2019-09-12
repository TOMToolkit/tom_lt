from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='tom-lt',
    version='0.1.0',
    description='Liverpool Telescope facility module for the TOM Toolkit',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://tom-toolkit.readthedocs.io',
    author='TOM Toolkit Project',
    author_email='dcollom@lco.global',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Topic :: Scientific/Engineering :: Astronomy',
        'Topic :: Scientific/Engineering :: Physics'
    ],
    keywords=['tomtoolkit', 'astronomy', 'astrophysics', 'cosmology', 'science', 'fits', 'observatory',
              'liverpool-telescope'],
    packages=find_packages(),
    install_requires=[
        'tomtoolkit',
        'suds-py3',
        'lxml',
    ],
    include_package_data=True,
)