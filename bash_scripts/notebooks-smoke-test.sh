#!/usr/bin/env bash

# text colours
PLAIN='\033[0m'
EM='\033[0;93m'
QUOTE='\033[0;34m'
SUCCESS='\033[0;32m'
FAILURE='\033[0;31m'

CHECKMARK_SYMBOL='\xE2\x9C\x94'
CROSS_SYMBOL='\xE2\x9D\x8C'

function print-result-symbol() {
  exit_code=$1
  if test $exit_code -eq 0
  then
    printf "${SUCCESS}${CHECKMARK_SYMBOL}${PLAIN}"
  else
    printf "${FAILURE}${CROSS_SYMBOL}${PLAIN}"
  fi
}

pushd "${0%/*}"/..

printf "Installing a Jupyter kernel for genet...\n"
ipython kernel install --name "genet" --user
printf "Looking for notebooks...\n"

find notebooks -type f -name '*.ipynb' -maxdepth 1 -print0 | sort |
while IFS= read -r -d '' file; do
    printf "\nFound '$file'"
done
echo ""

nb_count=0
find notebooks -type f -name '*.ipynb' -maxdepth 1 -print0 | sort |
{
    while IFS= read -r -d '' file; do
        printf "${PLAIN}-----------------------------------------------------------\n"
        nb_count=$(expr $nb_count + 1)
        printf "Notebook ${EM}$nb_count${PLAIN}"
        printf "\nExecuting ${EM}$file${QUOTE}\n"
        jupyter nbconvert --to notebook --execute "$file" --output-dir=/tmp
        exit_code=$?
        printf "${EM}$file${PLAIN} exit code was ${EM}$exit_code${PLAIN}\n"
    done

    printf "\n\nExecuted ${EM}$nb_count${PLAIN} notebooks - finished the smoke test\n"
}
popd
