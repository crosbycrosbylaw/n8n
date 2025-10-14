
$n8n = @{
  name = 'n8n.service'
  path = (get-command 'pixi').path
  args = 'run n8n'
  root = (join-path $psscriptroot '..')
  proc = $null
}

function start-n8n {
  return start-process -filepath $n8n.path $n8n.args `
    -workingdirectory $n8n.root -windowstyle hidden -passthru
}

start-job -name 'n8n.service' -scriptblock {
  while ($true) { if (!$n8n.proc -or $n8n.proc.hasexited) { $n8n.proc = start-n8n } }
}
