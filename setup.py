import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

setup(name='mojo_api',
      version='0.2',
      description='Mojo api',
      long_description='Mojo api',
      classifiers=[
        "Programming Language :: Python",
        ],
      author='Wei Shi',
      author_email='wshi@redhat.com',
      url='',
      keywords='mojo api',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      entry_points="""\
      [console_scripts]
      mojo = mojo_api.mojo_report:main
      """,
      )
