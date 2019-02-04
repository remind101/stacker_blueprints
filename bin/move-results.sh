#!/bin/bash

for file_path in tests/fixtures/blueprints/*-result; do
    # create new_file_path by removing -result from file_path.
    new_file_path=${file_path%-result}
    mv $file_path $new_file_path
done
