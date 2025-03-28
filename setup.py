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
        'python-docx',
    ],
    entry_points={
        "console_scripts": [
            "fileai-process=fileai.fileai_process:main",
            "fileai-dedupe=fileai.fileai_dedupe:main",
        ],
    },
    package_data={
        "": ["fileai.service"],
    },
    include_package_data=True,
)
