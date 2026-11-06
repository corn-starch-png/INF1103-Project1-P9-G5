# ONLY ONE yml file in workflow (save my github usage limit)

# DO NOT CHANGE DIRECTORY OF ANY FILES
If you need to change, kindly update the relative path in all the files

# DO NOT FIDDLE WITH docker_input.txt
the bash script is expecting a specific output from the docker output 
what i am grepping (note the white space)
| grep -Fq 'Household summary:' \
   && echo "$output" | grep -Fq '  1. Rick, 70, Male, diet: none' \
   && echo "$output" | grep -Fq '  2. Morty, 15, Male, diet: none';

# use checkout @v6 (latest version)

# why gitleaks when github native code protection exist?
Because gitleaks catches more leaks.
in .env.example, try commiting API_KEY=sk_test_7f9a2c8e4d1b6a3f0c9e5d2b8a6f4c1e
github code protection allows it, but gitleaks fails it on CI piepline 