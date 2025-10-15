[CmdletBinding()]
param(
  [parameter()]
  [validateset('start', 'stop', 'reload', 'status', 'monitor', 'poll')]
  $action = 'monitor'
)

$n8n = @{
  name = 'n8n.service'
  path = (get-command 'pixi').source
  args = 'run n8n'
  root = (join-path $psscriptroot '..')
}

$scripts = @{
  start  = {
    $procs = get-process 'node' -erroraction silentlycontinue
    if (!$procs) {
      start-process -filepath $n8n.path $n8n.args -workingdirectory $n8n.root `
        -windowstyle hidden
    }
  }
  stop   = {
    $procs = get-process 'node' -erroraction silentlycontinue
    if ($procs) { $procs | stop-process }
  }
  reload = {
    & $scripts.stop
    start-sleep 10
    & $scripts.start
  }
}

$path = join-path $psscriptroot 'service.ps1'

switch ($action) {
  'start' { & $scripts.start }
  'stop' { & $scripts.stop }
  'reload' { & $scripts.reload }
  'status' {
    get-process 'node' -erroraction silentlycontinue |
      where-object commandline -like '*n8n*' | where-object commandline -notlike '*task*'
  }
  'poll' {
    $ct = 0; while ($ct -lt 5) { & $path status; start-sleep 5; $ct += 1 }
  }
  'monitor' {
    while ($true) { if (!(& $path status)) { & $path start; start-sleep 30 }; start-sleep 20 }
  }
}
