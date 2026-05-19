from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

setup(
	name="quiz_crm",
	version="0.0.1",
	description="Quiz and Question management for CRM",
	author="OurEdu",
	author_email="dev@ouredu.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
)
