#!/bin/bash -i

set -ex
set -o allexport

. user_environment.sh

fuzz=false
fuzz_time=false
merge=false
git_commit=false
clean=false

print_usage() {
  echo "Usage: ./generate_database.sh <flags>"
  echo "Flags:"
  echo " -f - Run each fuzzer and store the results to their local fuzzer db"
  echo " -c - Clean before rerunning each fuzzer"
  echo " -m - Merge the local fuzzer db into the global db"
  echo " -g - Run git commit as the local fuzzers are merged."
}

while getopts 'fgmc' flag; do
  case "${flag}" in
    f) fuzz=true ;;
    m) merge=true ;;
    c) clean=true ;;
    g) git_commit=true ;;
    *) print_usage
       exit 1 ;;
  esac
done

pushd tools
#python3 tilegrid_all.py
popd

PRJOXIDE_ROOT=`pwd`

run_fuzzer() {
    dir="$1"
    if [ -f "$dir/fuzzer.py" ]; then
        set -ex

        echo "=================== Entering $dir ==================="
        pushd "$dir" > /dev/null || return

        if [ "$fuzz" = true ] ; then
          if [ "$clean" = true ] ; then
            rm -rf db .deltas
            $PRJOXIDE_ROOT/link-db-root.sh
          fi
          FUZZER_TITLE=$dir PRJOXIDE_DB="$(pwd)/db" python3 fuzzer.py 2>&1 | tee >(gzip --stdout > fuzzer.log.gz)
        fi
        popd > /dev/null || true

	MERGE_MSG=""
        if [ -d "$dir/db" ]; then
          if [ "$merge" = true ] ; then
            pushd ..

            find "fuzzers/$dir/db" -type f -name '*.json' ! -path "*/overlays.d/*" | while read -r file; do
	      dest="database/${file#fuzzers/$dir/db/}"
              cp "$file" "$dest" | true
            done

            MERGE_MSG=$(python3 ./tools/merge-databases.py fuzzers/$dir/db database/ 2>&1)
            popd
          fi

          if [ "$git_commit" = true ] ; then
            pushd ../database
            find | grep ron$ | xargs git add
            find | grep json$ | xargs git add
            git commit --allow-empty -m "Incorporating database changes from $dir" -m "$MERGE_MSG"
            popd
          fi
        fi

    fi
}
export -f run_fuzzer

pushd fuzzers

find . -mindepth 1 -maxdepth 2 -type d \
| awk -F'/' '
    # case 1: top-level dir like ./000-foo (only depth 1)
    NF == 2 && $2 ~ /^[0-9]+-/ {
        split($2, a, "-")
        printf "%05d %s\n", a[1], $0
        next
    }

    # case 2: subdir like ./FOO/010-bar (must match itself)
    NF == 3 && $3 ~ /^[0-9]+-/ {
        split($3, a, "-")
        printf "%05d %s\n", a[1], $0
    }
' \
| sort \
| cut -d' ' -f2- \
| xargs -I {} bash -c 'run_fuzzer "{}"'
