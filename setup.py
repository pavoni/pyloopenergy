
from setuptools import setup, find_packages

setup(name='pyloopenergy',
      version='0.0.12',
      description='Access Loop Energy energy monitors via Socket.IO API',
      url='http://github.com/pavoni/pyloopenergy',
      author='Greg Dowling',
      author_email='mail@gregdowling.com',
      license='MIT',
      install_requires=['socketIO-client==0.5.6'],
      packages=find_packages(),
      zip_safe=True)
