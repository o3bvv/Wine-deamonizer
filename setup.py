from setuptools import setup

setup(
    name='wine-deamonizer',
    version='1.0.1',
    description='Run Windows processes under Wine as Unix daemons.',
    license='GPLv2',
    url='https://github.com/oblalex/Wine-deamonizer',
    author='Alexander Oblovatniy',
    author_email='oblovatniy@gmail.com',
    packages=['wine_deamonizer'],
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'License :: Free for non-commercial use',
        'Natural Language :: English',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2.7',
        'Environment :: Console',
    ],
)
