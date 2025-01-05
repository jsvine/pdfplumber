#!/bin/bash -eu

cd "$SRC"/pdfplumber
pip3 install .

# Build fuzzers in $OUT
for fuzzer in $(find fuzz -name '*_fuzzer.py');do
  compile_python_fuzzer "$fuzzer"
done

mkdir -p fuzz/corpus
find . -name "*.pdf" -exec cp "{}" fuzz/corpus \;
zip -q $OUT/pdf_load_fuzzer_seed_corpus.zip fuzz/corpus/*
