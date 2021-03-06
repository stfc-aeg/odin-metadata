import sys
from setuptools import setup, find_packages
import versioneer

install_requires = [
    'odin>=1.0.0',
    'pyzmq>=22.0',
    'h5py'
]

extras_require = {
    'test': [
        'pytest', 'pytest-cov', 'requests', 'tox'
    ]
}

if sys.version_info[0] == 2:
    extras_require['test'].append('mock')

setup(
    name="odin-metadata",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description='ODIN Control Metadata Adapter',
    url='https://github.com/stfc-aeg/odin-metadata',
    author='Ashley Neaves',
    author_email='ashley.neaves@stfc.ac.uk',
    packages=find_packages('src'),
    package_dir={'':'src'},
    install_requires=install_requires,
    extras_require=extras_require,
)
