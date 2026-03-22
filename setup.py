from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-xiaoyuzhoufm",
    version="1.0.0",
    description="CLI-Anything: XiaoYuZhou FM (小宇宙FM) podcast platform CLI",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    package_data={
        "cli_anything.xiaoyuzhoufm": ["skills/*.md"],
    },
    install_requires=[
        "click>=8.0.0",
        "prompt-toolkit>=3.0.0",
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-anything-xiaoyuzhoufm=cli_anything.xiaoyuzhoufm.xiaoyuzhoufm_cli:main",
        ],
    },
    python_requires=">=3.9",
)
