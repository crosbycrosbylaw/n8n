[CmdletBinding()]
param(
  [parameter(mandatory)]
  [validateset('start', 'stop', 'reload', 'status', 'install')]
  $action = 'install'
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
    nssm install "${n8n.name}" "${n8n.path}"
    nssm set $n8n.name AppParameters "${n8n.args}"
    nssm set $n8n.name AppDirectory "${n8n.root}"
  }
  'start' { & $scripts.start }
  'stop' { & $scripts.stop }
  'reload' { & $scripts.reload }
  'status' { get-job $n8n.name }
}
