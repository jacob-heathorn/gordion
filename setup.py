import setuptools


setuptools.setup(
    name='gordion',
    version='0.1.0',
    author='Jacob Heathorn',
    author_email='todo@gmail.com',
    description='TODO',
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
    ],
    python_requires='>=3.8',
    entry_points={'console_scripts': ('gordion = gordion.app.main:main',)},
    zip_safe=False
)
