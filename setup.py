from setuptools import setup

setup(
    name='SC2ApiWrapper',
    version='0.11',
    description='Simple wrapper for sc2api-proto in python',
    url='https://github.com/MMandirola/SC2BlizzardWrapper',
    author='Felipe Lopez, Marcelo Mandirola, Marcelo Siccardi',
    author_email='fglf18@gmail.com, mandirolamarcelo@gmail.com, marcelosiccardi@gmail.com',
    license='MIT',
    install_requires=[
        'protobuf',
        's2clientprotocol',
        'six',
        'portpicker',
        'websocket-client',
        'websockets',
        'pympler'
    ],
    packages=['sc2_wrapper'],
    zip_safe=False
)
