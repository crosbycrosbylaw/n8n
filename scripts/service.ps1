[string]$nssm_path = (get-command 'nssm').path
function invoke-nssm { & $nssm_path @args }

$n8n = @{
  name = 'n8n.service'
  path = (get-command 'pixi').path
  args = "run $((get-command 'bun').path) x n8n"
  root = (join-path $psscriptroot '../service')
}

invoke-nssm install $n8n.name $n8n.path
invoke-nssm set $n8n.name AppDirectory $n8n.root
invoke-nssm set $n8n.name AppParameters $n8n.args
invoke-nssm set $n8n.name Start SERVICE_AUTO_START