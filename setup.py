from setuptools import setup, find_packages

setup(
    name="SC2ApiWrapper",
    version="2.0.1",
    description="Simple wrapper for sc2api-proto in python",
    url="https://github.com/MMandirola/SC2BlizzardWrapper",
    author="Felipe Lopez, Marcelo Mandirola, Marcelo Siccardi",
    author_email="fglf18@gmail.com, mandirolamarcelo@gmail.com, marcelosiccardi@gmail.com",
    license="MIT",
    install_requires=[
        "protobuf",
        "s2clientprotocol",
        "six",
        "portpicker",
        "websocket-client",
        "websockets",
        "pympler",
    ],
    packages=["sc2_wrapper", "sc2_wrapper.api_wrapper", "sc2_wrapper.constants", "sc2_wrapper.game_data", "sc2_wrapper.players"],
    zip_safe=False,
)
