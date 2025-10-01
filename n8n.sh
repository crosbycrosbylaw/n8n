CURRENT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

CMD="${2}"
LINES="${3}"

if command -v 'nohup' 2>&1 /dev/null; then
    echo "running node script"
    nohup { node -- "${CURRENT_DIR}/scripts/serve-n8n.mjs" $CMD } &
else
    echo "nohup not found"
    echo "to install, run 'sudo apt-get update && sudo apt-get install coreutils'"
fi