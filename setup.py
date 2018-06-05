from setuptools import setup

setup(name='SC2ApiWrapper',
      version='0.1',
      description='Simple wrapper for sc2api-proto in python',
      url='https://github.com/MMandirola/SC2BlizzardWrapper',
      author='Marcelo Mandirola, Marcelo Siccardi',
      author_email='mandirolamarcelo@gmail.com, marcelosiccardi@gmail.com',
      license='MIT',
      install_requires=[
        'protobuf',
        's2clientprotocol',
        'six',
        'portpicker',
        'websocket-client',
        'websockets',
      ],
      packages=['api_wrapper', 'game_data', 'players'],
      zip_safe=False)