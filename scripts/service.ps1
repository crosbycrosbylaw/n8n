[CmdletBinding()]
param(
    [parameter(position=0)][string]$action = 'status',
    [parameter()][int]$count = 5
)

$SCRIPT = join-path $psscriptroot 'service.ps1'
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

[int]$timeout = 60
[int]$interval = 10
[int]$max_attempts = ($timeout - $interval) / $interval

[int]$script:current = 0

if ($count -gt 0) {
    [scriptblock]$shouldcontinue = { $script:current -le $count }
    [scriptblock]$beforecontinue = { $script:current += 1 }
} else {
    [scriptblock]$shouldcontinue = { $true }
    [scriptblock]$beforecontinue = { }
}

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
        while (&$shouldcontinue) {
            get-n8n | write-output
            start-sleep $interval

            &$beforecontinue
        }
    }

    'monitor'  {
        while (&$shouldcontinue) {
            $running = [bool]$(get-n8n)

            if (!$running) {
                write-output '[n8n] service not detected; attempting reload'
                & $script reload ; start-sleep $timeout
            }

            start-sleep $interval

            &$beforecontinue
        }

    }

    default {
        write-host -foregroundcolor red -nonewline 'error: '
        write-host "could not find a script matching '$action'"
    }
}
