[CmdletBinding()]
param(
  [parameter(mandatory)]
  [validateset('start', 'stop', 'reload', 'status')]
  $action
)

$n8n = @{
  name = 'n8n.service'
  path = (get-command 'pixi').path
  args = 'run n8n'
  root = (join-path $psscriptroot '..')
}

$scripts = @{
  start  = {
    start-job -name $n8n.name -scriptblock {
      start-process -filepath $n8n.path $n8n.args -workingdirectory $n8n.root -windowstyle hidden
      while ($true) {
        $dead = [string]::isnullorempty((get-process 'node' -erroraction silentlycontinue))
        if ($dead) { start-process -filepath $n8n.path $n8n.args -workingdirectory $n8n.root -windowstyle hidden -passthru - }
        start-sleep 30
      }
    }
  }
  stop   = {
    $job = get-job $n8n.name -erroraction silentlycontinue
    if ($job) { $job.stopjob(); $job | remove-job }
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
  'status' { get-job $n8n.name }
}
