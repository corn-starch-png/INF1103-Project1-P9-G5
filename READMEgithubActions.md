# pipeline configuration
use checkout @v6 (latest version)
ONLY ONE yml file in workflow (save my github usage limit)
DO NOT CHANGE DIRECTORY OF ANY FILES
If you need to change, kindly update the relative path in all the files

# git leaks
# #why gitleaks when github native code protection exist?
Defense in depth, 
in .env.example, try commiting the test API key provided in the final report
github code protection allows it, but gitleaks fails it on CI piepline #git.

# pip-audit
https://github.com/pypa/gh-action-pip-audit/blob/main/README.md


# pytest
133 testcases on custom pytest.py 
average runtime around 1 second 


# Docker smoketest
# # DO NOT FIDDLE WITH docker_input.txt
the bash script is expecting a specific output from the docker output 
what i am grepping (note the white space)
| grep -Fq 'Household summary:' \
   && echo "$output" | grep -Fq '  1. Rick, 70, Male, diet: none' \
   && echo "$output" | grep -Fq '  2. Morty, 15, Male, diet: none';



  
-


