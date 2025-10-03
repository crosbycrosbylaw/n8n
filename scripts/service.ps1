[string]$nssm_path = (get-command 'nssm').path
function invoke-nssm { & $nssm_path @args }


$n8n = @{
  name = 'n8n.service'
  path = (get-command 'node').path
  args = (join-path $psscriptroot '../server/bin/serve.mjs')
  root = (join-path $psscriptroot '../server/bin')
}

invoke-nssm install $n8n.name $n8n.path $n8n.args
invoke-nssm set $n8n.name AppDirectory $n8n.root
invoke-nssm set $n8n.name Start SERVICE_AUTO_START