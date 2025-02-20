#!/usr/bin/env bash

# Check for custom number of stations
if [ $# -lt 1 ]; then
  echo -e "\033[0;31mUsage: $0 <number_of_stations>\033[0m"
  exit 1
fi

numStations=$1

# Step 1: Compile the C program
echo -e "\033[0;32mCompiling buildrandomtimetables.c...\033[0m"
cc -Wall -Werror -o buildrandomtimetables buildrandomtimetables.c
if [ $? -ne 0 ]; then
  echo -e "\033[0;31mCompilation failed. Exiting.\033[0m"
  exit 1
fi
sleep 0.5

# Step 2: Run the buildrandomtimetables executable with the custom number of stations
echo -e "\033[0;32mRunning buildrandomtimetables with $numStations stations...\033[0m"
./buildrandomtimetables $numStations
if [ $? -ne 0 ]; then
  echo -e "\033[0;31mRunning buildrandomtimetables failed. Exiting.\033[0m"
  exit 1
fi
sleep 0.5

# Step 3: Make assignports.sh executable
echo -e "\033[0;34mMaking assignports.sh executable...\033[0m"
chmod +x assignports.sh
sleep 0.5

# Step 4: Run assignports.sh with adjacency and startstations.sh as arguments
echo -e "\033[0;34mRunning assignports.sh...\033[0m"
./assignports.sh adjacency startstations.sh
if [ $? -ne 0 ]; then
  echo -e "\033[0;31mRunning assignports.sh failed. Exiting.\033[0m"
  exit 1
fi
sleep 0.5

# Step 7: Read the configurations from startstations.sh and run station-server.py for each
echo -e "\033[0;34mReading configurations from startstations.sh...\033[0m"
configs=()
while IFS= read -r line; do
    config=$(echo $line | sed -e 's/^\.\///' -e 's/ &//')
    configs+=("$config")
done < startstations.sh

> server_pids.txt

for config in "${configs[@]}"; do
    args=($config)
    args=("${args[@]:1}")
    echo -e "\033[0;36m-> Running station-server.py with configuration: ${args[*]}\033[0m"
    sleep 0.5
    python3 station-server.py "${args[@]}" &
    echo $! >> server_pids.txt
    sleep 0.5
done

echo -e "\033[0;35mAll station servers are running in the background. Shut down in 3 minutes. (Testing:10s)\033[0m"
sleep 0.5
echo -e "\033[0;32mSetup completed successfully.\033[0m"

sleep 180
while read pid; do
    kill -SIGTERM $pid
    wait $pid  # Optional: wait for the process to exit
done < server_pids.txt

echo -e "\033[0;31mAll servers have been shut down.\033[0m"
sleep 0.5
# Run the remove_test_file.sh script
echo -e "\033[0;34mRunning remove_test_file.sh...\033[0m"
sleep 0.5
./remove_test_file.sh
if [ $? -ne 0 ]; then
    echo -e "\033[0;31mFailed to run remove_test_file.sh.\033[0m"
else
    echo -e "\033[0;32mSuccessfully ran remove_test_file.sh.\033[0m"
fi

rm -f server_pids.txt