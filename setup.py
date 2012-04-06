from setuptools import setup, find_packages
try:
    from openproximity import __version__
except:
    import sys
    sys.path.append('src')
    from openproximity import __version__
    sys.path.remove('src')


PACKAGES=find_packages('src')+['locale']
REQUIRES=[
    'simplejson',
    'lxml',
    #'dbus-python',
    'django>=1.3,<1.4',
    'openproximity-external-media',
    'wadofstuff-django-serializers-op',
    'PyOFC2-op',
    'rpyc-op',
    'aircable-library-op',
    'django-notification-op',
    'django-cpserver-op',
    'openproximity-plugin-test',
    'rpyc-op',
    'django-configglue',
    'south',
    'django-rosetta',
    'django-mailer',
    'django-extensions',
    'django-restapi-op',
    'poster',
    'django-timezones-op',
]

setup(name = "OpenProximity",
      version = __version__,
      author = "Naranjo Manuel Francisco",
      author_email = "manuel@aircable.net",
      description = ("OpenProximity an OpenSource proximity marketing solution"),
      license = "Apache V2",
      packages = PACKAGES,
      package_dir = { '': 'src'},
      keywords = "openproximity bluetooth obex proximity marketing",
      url = "https://github.com/OpenProximity/web",
      include_package_data = True,
      install_requires = REQUIRES,
      zip_safe = True,
      entry_points = {
        'console_scripts': [
            'OpenProximity-manage = openproximity.lib.manage:main',
            ],
        },
)

#    package_data={
#        "openproximity": [
#            "src/*.cfg",
#            "src/locale/*",
#            "src/microblog/templates/*",
#            "src/openproximity/templtates/*",
#            "src/openproximity/static/*"
#        ]
#    },
