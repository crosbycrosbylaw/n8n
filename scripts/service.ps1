[CmdletBinding()]
param(
    [parameter()]
    [validateset('start', 'stop', 'reload', 'status', 'monitor', 'poll')]
    $action = 'status'
)

$SCRIPT = join-path $psscriptroot 'service.ps1'


[int]$timeout = 60
[int]$interval = 10
[int]$max_attempts = ($timeout - $interval) / $interval

$SVC = @{
    name = 'n8n.service'
    path = (get-command 'bun').source
    args = 'start'
    root = (join-path $psscriptroot '..' 'service')
}

function get-n8n() {
    get-process 'node' -erroraction silentlycontinue |
        where-object commandline -like '*n8n*' | where-object commandline -notlike '*task*'
}

function start-n8n() {
    start-process -filepath $svc.path $svc.args -workingdirectory $svc.root
}

$procs = get-n8n
$running = [bool]$procs

switch ($action) {

    'start'  {

        if ($procs) { return '[n8n] service is already running' }

        write-output '[n8n] starting service...'

        start-n8n
        start-sleep $interval

        $running = [bool]$(get-n8n)

        if ($running) {
            return '[n8n] service started successfully'
        } else {
            write-output '[n8n] service is not yet ready'
        }

        $count = 0

        while (!$running -and ($count -lt $max_attempts)) {
            $running = [bool]$(get-n8n)
            $count += 1

            if ($running) { return '[n8n] service started successfully' }

            write-output "[n8n] waiting for process (attempt: ${count}/${$max_attempts})"
            start-sleep $interval
        }

        if (!$running) { write-output '[n8n] service startup was unsuccessful' }

    }

    'stop'  {

        if ($procs) { $procs | foreach-object {
                $psitem.kill()
                $psitem.waitforexit() }

            write-output 'service terminated'

        } else {
            write-output 'service is not running'
        }

    }

    'reload'  {
        & $script stop | out-null ; start-sleep $interval ; & $script start | out-null
    }

    'status'  {
        if ($procs) { $procs | write-output } else { return '[n8n] service is down' }
    }

    'poll'  {
        while ($true) { get-n8n | write-output ; start-sleep $interval }
    }

    'monitor'  {

        while ($true) {

            $running = [bool]$(get-n8n)

            if (!$running) {
                write-output '[n8n] service not detected; attempting reload'
                & $script reload ; start-sleep $timeout
            }

            start-sleep $interval
        }

    }
}
