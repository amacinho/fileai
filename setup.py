from setuptools import setup, find_packages

setup(
    name="fileai",
    version="0.1.0",
    packages=['fileai'],
    package_dir={'fileai': 'fileai'},
    install_requires=[
        "google-genai",
        "pydantic",
        "python-dotenv",
        "pillow",
        "pdf2image",
        "PyPDF2",
        "inotify",
        'docx',
    ],
    entry_points={
        "console_scripts": [
            "fileai=fileai.main:main",
        ],
    },
    package_data={
        "": ["fileai.service"],
    },
    include_package_data=True,
)
