try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name="django-approval",
    version="0.15.1",
    description="Easily moderate any content in Django before it's visible to the public.",
    long_description=open("README.md").read(),
    author="Steve Kossouho",
    license="MIT",
    author_email="skossouho@dawan.fr",
    url="https://github.com/artscoop/django-approval",
    install_requires=["Django>=3.2"],
    package_dir={"": "src"},
    packages=[
        "approval",
        "approval.admin",
        "approval.forms",
        "approval.listeners",
        "approval.models",
        "approval.templatetags",
    ],
    package_data={"approval": ["locale/*/LC_MESSAGES/*.po", "templates/**/*.html"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: Django",
    ],
    extras_require={
        "drf": ["django-rest-framework", "rest-framework-generic-relations"],
    },
)
