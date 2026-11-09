# Pipeline introduction
The purpose of Quantifresh CI pipeline is to provide automated testing for code quality, security and functionality using multiple tools

###Pipeline ruleset###
The pipeline is configured to run on pushes to any branches AND on PR request targetting the main branch 

_What is blocked?_
For main branch, any jobs failing results in merge being blocked
For ALL branches, any *_security_* job failing will result in the push failing


# basic pipeline configuration
_Python image used: python:3.14-slim_
_vm used: Ubuntu latest_
use checkout @v6 (latest version as of Nov 2026)
*ONLY yml files for pipelines* in workflow folder, prevents spinning up unwanted workflows.

DO NOT CHANGE DIRECTORY OF ANY FILES,
If you need to change, kindly check and update the directories in CiPipeline.yml.

###smoke_test###
Relevant directory changes has to be reflected in both docker-compose.ci.yml AND docker-smoke-test.sh. 

*DO NOT* modify docker_input.txt.

If you really need to, Modify docker_input.txt AND docker-smooke-test.sh together.
The bash script is expecting a specific output from the docker output or else the specific smoke test job WILL fail 

_what i am grepping (note the white space)_
>| grep -Fq 'Household summary:' \
>   && echo "$output" | grep -Fq '  1. Rick, 70, Male, diet: none' \
>   && echo "$output" | grep -Fq '  2. Morty, 15, Male, diet: none';

***


# git leaks
Security job, scans for exposed secrets in pipeline and flag out violations
(think of it as a gitblame but for who exposed the repository secrets)

_why gitleaks when github secret  protection exist?_
Defense in depth, some dummy secrets were not flagged by github native secret protection during testing 

technical documentation
https://github.com/gitleaks/gitleaks


# pip-audit
pip-audit is a tool for scanning Python environments for packages with known vulnerabilities. It uses the Python Packaging Advisory Database (https://github.com/pypa/advisory-database) via the PyPI JSON API as a source of vulnerability reports.

technical documentation 
https://github.com/pypa/gh-action-pip-audit/blob/main/README.md


# Linting with Ruff (code quality testing)
This job will always pass, it is used as a feedback job for team members to review their code
it is split into 3 sub jobs: advisory, enforced, formatting

###advisory###
all default rules applied, job will feedback on any rules violations in workflow logs

###enforced###
certain formatting rules removed, allows team member to view violations which are potentially more serious

###format###
Checks and reformat codes if needed, pumps out output in workflow logs

###why ruff was used###
> "Ruff can be used to replace Flake8 (plus dozens of plugins), Black, isort, pydocstyle, pyupgrade, autoflake, and more, all while executing tens or hundreds of times faster than any individual tool." 

_ignored rules: B904,B905,B007,E712,E501,E701,I001,F401,F541,F841,SIM102,RUF059,FURB157,PLC0206_
_ruff tehcnical documentation: https://docs.astral.sh/ruff/rules/ ._

# Pytest (Unit testing)
Custom automated testcase created by team member ZH. 
Runs twice on docker, once on python3.14 image and once on Quantifresh image. 
this arrangment ensures a fallback image for testing in case Quantifresh image fails to build. 

_133 testcases on custom pytest.py_
_average runtime of around 1 second_

technical documentation for pytest
https://docs.pytest.org/en/stable/


# Docker smoketest
The purpose of this job is to ensure the Quantifresh docker image can be built and respond to basic inputs.
This job build's Quantifresh docker image on the CI pipeline and feed it inputs from docker_input.txt. 
A bash script will grep the expected output and pass the job accordingly.


***

----------------------------------END OF DOCUMENTATION----------------------------------

***

