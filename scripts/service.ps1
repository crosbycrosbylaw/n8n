$n8n = @{
  name = 'n8n.service'
  path = (get-command 'pixi').path
  args = 'run n8n'
  root = (join-path $psscriptroot '..')
}

start-process -filepath $n8n.path $n8n.args -workingdirectory $n8n.root -nonewwindow