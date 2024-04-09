try:
    from setuptools import setup, Command, find_packages
    setuptools_available = True
except ImportError:
    from distutils.core import setup, Command, find_packages
    setuptools_available = False

#     packages=['music_kraken'],

#packages = find_packages(where="src")
packages = ['music_kraken', 'music_kraken.lyrics', 'music_kraken.not_used_anymore', 'music_kraken.target', 'music_kraken.metadata', 'music_kraken.tagging', 'music_kraken.utils', 'music_kraken.not_used_anymore.sources', 'music_kraken.database', 'music_kraken.static_files']

print("packages")
print(packages)
# packages.extend(["music_kraken.database"])

with open("README.md", "r") as readme_file:
    long_description = readme_file.read()

install_requires = [
    "requests~=2.28.1",
    "mutagen~=1.46.0",
    "musicbrainzngs~=0.7.1",
    "jellyfish~=0.9.0",
    "pydub~=0.25.1",
    "youtube_dl", 
    "beautifulsoup4~=4.11.1", 
    "pycountry~=22.3.5"
]

with open("requirements.txt", "r") as requirements_txt:
    install_requires = []
    for requirement in requirements_txt:
        requirement = requirement.strip()
        install_requires.append(requirement)
        print(requirement)

version = '1.2.1'
with open('version', 'r') as version_file:
    version = version_file.read()
    print(f"version: {version}")

setup(
    name='music-kraken',
    version=version,
    description='An extensive music downloader crawling the internet. It gets its metadata from a couple of metadata '
                'providers, and it scrapes the audiofiles.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Hellow2',
    author_email='Hellow2@outlook.de',
    url='https://github.com/HeIIow2/music-downloader',
    packages=packages,
    package_dir={'': 'src', 'music_kraken': 'src/music_kraken'},
    install_requires=install_requires,
    entry_points={'_scripts': ['music-kraken = music_kraken:cli']},
    include_package_data=True,
    package_data={'music_kraken': ['*.sql']},
    data_files=[
        ('', ['requirements.txt', 'README.md', 'version'])
    ]
)

# ('music_kraken', ['static_files/database_structure.sql']),

