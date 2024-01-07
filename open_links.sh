#!/bin/bash

# Replace with your CSV file path
FILE="properties.csv"
# Number of URLs to open in each batch
BATCH_SIZE=20
# Column number containing the URLs
COLUMN=1

# Calculate total lines, skipping the header if present
TOTAL_LINES=$(cat $FILE | wc -l)
((TOTAL_LINES--)) # Decrease count if there's a header

# Loop through the file in batches
for ((i=1; i<=$TOTAL_LINES; i+=$BATCH_SIZE)); do
    # Calculate the end line for the current batch
    END=$((i+BATCH_SIZE-1))
    [ $END -gt $TOTAL_LINES ] && END=$TOTAL_LINES

    # Extract a batch of URLs and open them
    tail -n +$i $FILE | head -n $BATCH_SIZE | awk -F, "{print \$$COLUMN}" | xargs -I {} open {}
    # Output the range of lines processed
    echo "Opened lines $i to $END. Press Enter to continue with the next batch..."
    read -p ""
done
