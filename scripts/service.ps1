[CmdletBinding()]
param(
  [parameter(mandatory)]
  [validateset('start', 'stop', 'reload', 'status', 'install')]
  $action = 'install'
)

$n8n = @{
  name = 'n8n.service'
  path = (get-command 'pixi').source
  args = 'run n8n'
  root = (join-path $psscriptroot '..')
}

$scripts = @{
  start  = {
    start-job -name $n8n.name -scriptblock {
      start-process -filepath $n8n.path $n8n.args -workingdirectory $n8n.root -windowstyle hidden
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
  'install' {
    nssm install $n8n.name $((get-command 'pixi').source)
    nssm set $n8n.name AppParameters 'run n8n'
    nssm set $n8n.name AppDirectory $(join-path $psscriptroot '..')
  }
  'start' { & $scripts.start }
  'stop' { & $scripts.stop }
  'reload' { & $scripts.reload }
  'status' { get-job $n8n.name }
}
