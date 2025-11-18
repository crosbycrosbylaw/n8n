using namespace system.collections.generic

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

function write-prefixed(
    [parameter(valuefrompipeline)]
    [object[]]$inputobject,
    [parameter(valuefromremainingarguments)]
    [string[]]$messages
) {
    [string]$dt = $(get-date).tostring()
    [string]$text = $messages -join ' '

    if ($inputobject -and !$text) { $text = $inputobject -join ' '; $inputobject = $null }

    "[n8n] $dt | $text" | write-output
    if ($inputobject) { $inputobject | foreach-object { write-output $psitem } }
}

function get-n8nprocs() {
    get-process 'node' -erroraction silentlycontinue |
        where-object commandline -like '*n8n*' | where-object commandline -notlike '*task*'
}

function get-n8nstatus() {
    $resources = get-n8nprocs | select-object -p 'psresources'
    return $resources
}

function start-n8n() {
    start-process -filepath $svc.path $svc.args -workingdirectory $svc.root
}

function write-n8n() {

    if ($resources = get-n8nstatus) {
        $proc_id = $resources.id | join-string -sep ', '
        "service is running (pids: $proc_id)" | write-prefixed
        $resources | write-verbose
    } else {
        write-prefixed 'service is down'
    }

}


$script:procs = get-n8nprocs
$script:running = [bool]$procs

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

        if ($procs) { write-prefixed 'service is already running'; return }

        write-prefixed 'starting service...'

        start-n8n
        start-sleep $interval

        [scriptblock]$statusmsg = {
            param([int]$ct = $null)
            $script:running = [bool]$(get-n8nprocs)

            if ($script:running) {
                write-prefixed 'service started successfully'
            } elseif ($ct) {
                write-prefixed "waiting for process (attempt: ${ct}/${$max_attempts})"
            } else {
                write-prefixed 'service is not yet ready'
            }
        }

        &$statusmsg

        if ($script:running) { return }

        $count = 0

        while (!$script:running -and ($count -lt $max_attempts)) {
            &$statusmsg -ct $count
            $count += 1
            start-sleep $interval
        }

        if (!$script:running) { write-prefixed 'service startup was unsuccessful' }

    }

    'stop'  {

        if ($procs) { $procs | foreach-object {
                $psitem.kill()
                $psitem.waitforexit() }

            write-prefixed 'service terminated'

        } else {
            write-prefixed 'service is not running'
        }

    }

    'reload'  {
        & $script stop | out-null
        start-sleep $interval
        & $script start | out-null
    }

    'status'  {
        write-n8n
    }

    'poll'  {
        while (&$shouldcontinue) {


            write-n8n

            start-sleep $interval
            &$beforecontinue
        }
    }

    'monitor'  {
        while (&$shouldcontinue) {

            if (!$(get-n8nprocs)) {
                write-prefixed 'service not detected; attempting reload'
                & $script reload

                start-sleep $timeout
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
