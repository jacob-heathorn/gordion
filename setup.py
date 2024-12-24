import setuptools


setuptools.setup(
    name='gordion',
    version='0.1.0',
    author='Jacob Heathorn',
    author_email='jacob.heathorn@gmail.com',
    description='The place where the gordian knot is untied',
    packages=setuptools.find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
    ],
    install_requires=[
        'setuptools',
        'gitpython==3.1.43',
        'pyYAML',
        'types-PyYAML'
    ],
    python_requires='>=3.8',
    entry_points={'console_scripts': ('gordion = gordion.app.main:main',
                                      'gor = gordion.app.main:main')},
    zip_safe=False
)
