[string]$nssm = (get-command 'nssm').path

$service = @{
  name = 'n8n.service'
  exe  = (get-command 'node').path
  args = (join-path $psscriptroot '../server/bin/serve.mjs')
  cwd  = (join-path $psscriptroot '../server/bin')
}

& $nssm install $service.name $service.exe $service.args
& $nssm set $service.name AppDirectory $service.cwd
& $nssm set $service.name Start SERVICE_AUTO_START