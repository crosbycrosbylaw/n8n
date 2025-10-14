[CmdletBinding()]
param(
  [parameter(mandatory)]
  [validateset('start', 'stop', 'reload', 'status')]
  $action = 'status'
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
        -windowstyle hidden -nonewwindow -wait -passthru
    }
  }
  stop   = {
    $procs = get-process 'node' -erroraction silentlycontinue
    if ($procs) { $procs | stop-process }
  }
  reload = {
    & $scripts.stop
    & $scripts.start
  }
}




switch ($action) {
  'start' { & $scripts.start }
  'stop' { & $scripts.stop }
  'reload' { & $scripts.reload }
  'status' { get-job $n8n.name -erroraction silentlycontinue }
}
